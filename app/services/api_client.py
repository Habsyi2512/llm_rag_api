import httpx, tempfile, logging
from app.core.config import settings
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

headers = {
    "Authorization": f"Bearer {settings.LARAVEL_API_TOKEN}",
    "Accept" : "application/json"
    }

from app.services.vector_store.fetcher import fetch_faqs_from_api, fetch_documents_from_api, fetch_tracking_status_from_api
    
async def download_file_to_temp(relative_url: str, suffix: str = ".pdf") -> str:
    """
    Mengunduh file dari URL publik Laravel ke lokasi file temporer lokal.
    Mengembalikan path file temporer.
    """
    temp_path = None
    # Konstruksi URL lengkap
    corrected_url_path = relative_url.replace('public/', 'storage/')
    full_url = f"{settings.LARAVEL_PUBLIC_URL}/{corrected_url_path}"
    
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