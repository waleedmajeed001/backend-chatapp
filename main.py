from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import asyncpg
import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token handling
security = HTTPBearer()

app = FastAPI(title="Chat App API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

class Token(BaseModel):
    access_token: str
    token_type: str

# Database connection
async def get_db_connection():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

# Password utilities
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# JWT utilities
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    email = verify_token(token)
    
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

# Initialize database tables
async def init_db():
    conn = await get_db_connection()
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    finally:
        await conn.close()

@app.on_event("startup")
async def startup_event():
    await init_db()

# Routes
@app.post("/auth/signup", response_model=UserResponse)
async def signup(user_data: UserCreate):
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
        password_hash = get_password_hash(user_data.password)
        
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

@app.post("/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    conn = await get_db_connection()
    try:
        # Find user by email
        user = await conn.fetchrow(
            "SELECT id, username, email, password_hash FROM users WHERE email = $1",
            user_data.email
        )
        
        if not user or not verify_password(user_data.password, user['password_hash']):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user['email']}, expires_delta=access_token_expires
        )
        
        return Token(access_token=access_token, token_type="bearer")
    finally:
        await conn.close()

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    return current_user

@app.get("/")
async def root():
    return {"message": "Chat App API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
