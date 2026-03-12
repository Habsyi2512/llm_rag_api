from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

async def get_current_admin(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Dependency to verify JWT token and Return admin identity.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject",
            )
        # In a real app, you might check if the user exists in the database
        if email != settings.ADMIN_EMAIL:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authorized",
            )
        return email
    except JWTError as e:
        logger.warning(f"JWT Verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Maintain backward compatibility for routers that use verify_api_key name
async def verify_api_key(admin_email: str = Depends(get_current_admin)):
    return admin_email