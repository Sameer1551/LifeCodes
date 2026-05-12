import uvicorn
from fastapi import FastAPI, Depends
from pathlib import Path

from auth import router as auth_router, get_current_user
from config import settings

# Create the FastAPI app instance
app = FastAPI(
    title=settings.app_name,
    description="A lightweight FastAPI starter with JWT Authentication.",
    version="1.0.0",
)

# Register routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

@app.get("/ping")
async def ping():
    """Health check endpoint."""
    return {"msg": "pong"}

@app.get("/protected")
async def protected(user: str = Depends(get_current_user)):
    """A protected route that requires a valid JWT token."""
    return {"msg": f"Hello {user}, you are authenticated!"}

if __name__ == "__main__":
    # Run server with auto-reload
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
