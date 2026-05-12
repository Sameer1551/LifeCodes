import datetime
from datetime import timezone, timedelta
from typing import Any, Dict
import jwt

def create_access_token(
    data: Dict[str, Any], 
    secret: str, 
    algorithm: str = "HS256", 
    expires_delta: timedelta = None
) -> str:
    """
    Encodes a JWT.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(timezone.utc) + timedelta(hours=1)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=algorithm)
    return encoded_jwt

def decode_access_token(token: str, secret: str, algorithms: list = ["HS256"]) -> Dict[str, Any]:
    """
    Decodes a JWT. Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
    """
    payload = jwt.decode(token, secret, algorithms=algorithms)
    return payload
