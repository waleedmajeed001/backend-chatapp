from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from database.connection import init_db
from routes.auth_routes import router as auth_router
from routes.main_routes import router as main_router

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(title="Chat App API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(main_router)
app.include_router(auth_router)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
