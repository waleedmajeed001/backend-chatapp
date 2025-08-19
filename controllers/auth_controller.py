from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.user import UserCreate, UserLogin, UserResponse, Token
from services.auth_service import AuthService

# JWT token handling
security = HTTPBearer()

class AuthController:
    @staticmethod
    async def signup(user_data: UserCreate) -> UserResponse:
        """Handle user registration"""
        return await AuthService.create_user(user_data)

    @staticmethod
    async def login(user_data: UserLogin) -> Token:
        """Handle user authentication"""
        return await AuthService.authenticate_user(user_data)

    @staticmethod
    async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
        """Get current authenticated user"""
        token = credentials.credentials
        email = AuthService.verify_token(token)
        return await AuthService.get_user_by_email(email)


