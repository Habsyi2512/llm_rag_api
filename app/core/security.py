# app/core/security.py
from datetime import datetime, timedelta
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # If the stored password is not hashed (for simple demo/migration), we might want to handle it
    # But for production, always use hashed passwords.
    # Here we assume ADMIN_PASSWORD in env might be plain for simple setup, 
    # but we'll try to verify it properly.
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        # Fallback for plain text comparison if hashing fails (NOT RECOMMENDED for production)
        return plain_password == hashed_password

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
