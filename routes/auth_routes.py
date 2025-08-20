from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.user import UserCreate, UserLogin, UserResponse, Token
from services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

@router.post("/register", response_model=Token)
async def register(user: UserCreate):
    return await AuthService.register_user(user)

@router.post("/login", response_model=Token)
async def login(user: UserLogin):
    return await AuthService.login_user(user)

@router.get("/me", response_model=UserResponse)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    email = AuthService.verify_token(token)
    user = await AuthService.get_user_by_email(email)
    return user

@router.get("/users", response_model=list[UserResponse])
async def get_all_users(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get all registered users"""
    token = credentials.credentials
    email = AuthService.verify_token(token)
    user = await AuthService.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return await AuthService.get_all_users()


