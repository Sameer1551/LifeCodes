from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from passlib.context import CryptContext

from .config import settings
from .jwt_helper import create_access_token, decode_access_token

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

# Password context using bcrypt (standard for production)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In‑memory user store – replace with a database in production
# We pre-hash the password "supersecret" on startup
_USERS = {
    "bob@example.com": pwd_context.hash("supersecret")
}

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username
    password = form_data.password
    
    # 1. Verify user exists
    stored_hash = _USERS.get(email)
    if not stored_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 2. Verify password
    if not pwd_context.verify(password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Create Token
    access_token = create_access_token(
        data={"sub": email},
        secret=settings.jwt_secret,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return {"access_token": access_token, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Dependency to extract and validate the current user from a JWT token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token, secret=settings.jwt_secret)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return email
    except ValueError:
        raise credentials_exception
