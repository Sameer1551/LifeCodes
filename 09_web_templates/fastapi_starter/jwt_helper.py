import datetime
from datetime import timezone, timedelta
from typing import Any, Dict
from jose import JWTError, jwt

def create_access_token(data: Dict[str, Any], secret: str, expires_delta: timedelta) -> str:
    """
    Creates a JWT access token.
    """
    to_encode = data.copy()
    # Use timezone-aware datetime to avoid deprecation warnings
    expire = datetime.datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret, algorithm="HS256")
    return encoded_jwt

def decode_access_token(token: str, secret: str) -> Dict[str, Any]:
    """
    Decodes and validates a JWT token.
    Raises ValueError if the token is invalid.
    """
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        return payload
    except JWTError as exc:
        raise ValueError(f"Could not validate credentials: {exc}") from exc
