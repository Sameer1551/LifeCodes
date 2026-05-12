import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file automatically
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    
    # JWT Settings
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-jwt-secret-change-me")
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour in seconds

    # Flask Settings
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

class ProductionConfig(Config):
    DEBUG = False
    # In production, ensure SECRET_KEY and JWT_SECRET are set in environment

class DevelopmentConfig(Config):
    DEBUG = True
