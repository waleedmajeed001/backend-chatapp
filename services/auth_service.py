from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from typing import Optional
from fastapi import HTTPException
from database.connection import get_db_connection
from models.user import UserCreate, UserLogin, UserResponse, Token

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    @staticmethod
    def verify_password(plain_password, hashed_password):
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password):
        return pwd_context.hash(password)

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return email
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    @staticmethod
    async def create_user(user_data: UserCreate) -> UserResponse:
        conn = await get_db_connection()
        try:
            # Check if user already exists
            existing_user = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1 OR username = $2",
                user_data.email, user_data.username
            )
            
            if existing_user:
                raise HTTPException(
                    status_code=400, 
                    detail="User with this email or username already exists"
                )
            
            # Hash password and create user
            password_hash = AuthService.get_password_hash(user_data.password)
            
            user = await conn.fetchrow(
                """
                INSERT INTO users (username, email, password_hash)
                VALUES ($1, $2, $3)
                RETURNING id, username, email
                """,
                user_data.username, user_data.email, password_hash
            )
            
            return UserResponse(
                id=user['id'],
                username=user['username'],
                email=user['email']
            )
        finally:
            await conn.close()

    @staticmethod
    async def authenticate_user(user_data: UserLogin) -> Token:
        conn = await get_db_connection()
        try:
            # Find user by email
            user = await conn.fetchrow(
                "SELECT id, username, email, password_hash FROM users WHERE email = $1",
                user_data.email
            )
            
            if not user or not AuthService.verify_password(user_data.password, user['password_hash']):
                raise HTTPException(
                    status_code=401,
                    detail="Incorrect email or password"
                )
            
            # Create access token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = AuthService.create_access_token(
                data={"sub": user['email']}, expires_delta=access_token_expires
            )
            
            return Token(access_token=access_token, token_type="bearer")
        finally:
            await conn.close()

    @staticmethod
    async def get_user_by_email(email: str) -> UserResponse:
        conn = await get_db_connection()
        try:
            user = await conn.fetchrow(
                "SELECT id, username, email FROM users WHERE email = $1",
                email
            )
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            return UserResponse(id=user['id'], username=user['username'], email=user['email'])
        finally:
            await conn.close()

    @staticmethod
    async def get_all_users() -> list[UserResponse]:
        """Get all registered users"""
        conn = await get_db_connection()
        try:
            users = await conn.fetch(
                "SELECT id, username, email FROM users ORDER BY username"
            )
            return [
                UserResponse(id=user['id'], username=user['username'], email=user['email'])
                for user in users
            ]
        finally:
            await conn.close()

    @staticmethod
    async def register_user(user_data: UserCreate) -> Token:
        """Register a new user and return access token"""
        # Create user
        user = await AuthService.create_user(user_data)
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = AuthService.create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        return Token(access_token=access_token, token_type="bearer")

    @staticmethod
    async def login_user(user_data: UserLogin) -> Token:
        """Login user and return access token"""
        return await AuthService.authenticate_user(user_data)

