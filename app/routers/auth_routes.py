# app/routers/auth_routes.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.core.security import create_access_token, verify_password
from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["Authentication"])

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/login")
async def login(request: LoginRequest):
    # Check if credentials match (in production, check DB)
    if request.email != settings.ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    if not verify_password(request.password, settings.ADMIN_PASSWORD):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # Create JWT Token
    access_token = create_access_token(subject=request.email)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_HOURS * 3600
    }
