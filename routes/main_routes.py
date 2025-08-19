from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Chat App API is running"}

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running successfully"}
