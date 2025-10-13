from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Security(security)):
  """
    Dependency untuk memverifikasi API key dari header Authorization.
  """
  # Ambil token dari credentials
  token = credentials.credentials if credentials else None

  # Bandingkan dengan token yang disimpan di konfigurasi
  if token != settings.FASTAPI_API_KEY:
    logger.warning(f"Unauthorized access attempt with token: {token}")
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Invalid or missing API Key",
      headers={"WWW-Authenticate": "Bearer"}
    )
  logger.info("API Key verified successfully")
  return token