from fastapi import APIRouter, Depends
from models.user import UserCreate, UserLogin, UserResponse, Token
from controllers.auth_controller import AuthController

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/signup", response_model=UserResponse)
async def signup(user_data: UserCreate):
    """User registration endpoint"""
    return await AuthController.signup(user_data)

@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """User login endpoint"""
    return await AuthController.login(user_data)

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserResponse = Depends(AuthController.get_current_user)):
    """Get current user information (protected endpoint)"""
    return current_user
