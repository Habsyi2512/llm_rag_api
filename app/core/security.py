import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from app.core.config import settings

# Zona waktu WIB (UTC+7)
WIB = timezone(timedelta(hours=7))

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    now = datetime.now(WIB)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Check if it's already a bcrypt hash (starts with $2b$)
        if hashed_password.startswith("$2") or hashed_password.startswith("$2b$"):
            return bcrypt.checkpw(
                plain_password.encode("utf-8"), 
                hashed_password.encode("utf-8")
            )
        # Fallback for plain text (e.g. from initial setup/env)
        return plain_password == hashed_password
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def get_password_hash(password: str) -> str:
    # Ensure password is not over 72 bytes for bcrypt
    pwd_bytes = password.encode("utf-8")
    if len(pwd_bytes) > 72:
        # Option 1: Truncate (commonly done)
        # Option 2: Error (safer if user needs to know)
        # We'll truncate to match standard bcrypt behavior but avoid direct ValueError
        pwd_bytes = pwd_bytes[:72]
    
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")
