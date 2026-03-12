import httpx, tempfile, logging
from app.core.config import settings
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

headers = {
    "Authorization": f"Bearer {settings.LARAVEL_API_TOKEN}",
    "Accept" : "application/json"
    }

from app.services.vector_store.fetcher import fetch_faqs_from_api, fetch_documents_from_api, fetch_tracking_status_from_api
    
import os

async def download_file_to_temp(relative_url: str, suffix: str = ".pdf") -> str:
    """
    Returns the local path if the file exists locally, otherwise downloads it into a temp file.
    """
    # 1. Jika URL adalah path lokal yang sudah ada (misal: uploads/file.pdf)
    if os.path.exists(relative_url):
        return relative_url
        
    temp_path = None
    
    # 2. Jika bukan path lokal, asumsikan itu adalah sisa-sisa URL Laravel lama
    full_url = relative_url
    if relative_url.startswith("public/"):
        corrected_url_path = relative_url.replace('public/', 'storage/')
        full_url = f"{settings.LARAVEL_PUBLIC_URL}/{corrected_url_path}"
    elif not full_url.startswith("http"):
        # Jika tidak ada path lokal & bukan URL, berarti ada kesalahan database path
        logger.error(f"File lokal tidak ditemukan dan bukan URL HTTP: {relative_url}")
        raise RuntimeError(f"File tidak ditemukan lokal: {relative_url}")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(full_url)
            response.raise_for_status() # Raise untuk 4xx/5xx errors

            # Membuat dan menulis ke file temporer
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            temp_file.write(response.content)
            temp_file.close()
            temp_path = temp_file.name
            
            logger.info(f"Successfully downloaded file from {full_url} to {temp_path}")
            return temp_path
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Error {e.response.status_code} accessing URL: {full_url}")
        # Angkat Runtime Error untuk ditangani oleh pemanggil
        raise RuntimeError(f"Gagal mengunduh file: {e}")
    except Exception as e:
        logger.exception(f"Error during file download from {full_url}")
        raise RuntimeError(f"Gagal koneksi atau I/O saat mengunduh: {e}")



if __name__ == "__main__":
  data =  fetch_faqs_from_api()
  print(data)