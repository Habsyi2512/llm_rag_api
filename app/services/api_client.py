import httpx, tempfile, logging
from app.core.config import settings
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

headers = {
    "Authorization": f"Bearer {settings.LARAVEL_API_TOKEN}",
    "Accept" : "application/json"
    }

async def fetch_faqs_from_api() -> List[Dict[str, Any]]:
  """Mengambil data FAQ dari API Laravel."""
  url = f"{settings.LARAVEL_API_BASE_URL}/faqs"
  # timeout = httpx.Timeout(settings.LARAVEL_API_TIMEOUT)

  try:
    async with httpx.AsyncClient() as client:
      response = await client.get(url, headers=headers)
      response.raise_for_status()
      data = response.json()
      # Asumsi API mengembalikan data dalam format {  [...] }
      faqs = data.get('data', data) # Fallback jika struktur berbeda
      processed_faqs = []
      for item in faqs:
        # Gabungkan question dan answer sebagai satu dokumen
        content = f"Pertanyaan: {item.get('question', '')}\nJawaban: {item.get('answer', '')}"
        processed_faqs.append({
          "page_content": content,
          "id": item.get('id', ''), 
          "metadata" : {
            "source": "faq",
            "id" : item.get('id', '')
          }
        })
      return processed_faqs
    
  except httpx.HTTPStatusError as e:
        print(f"Error fetching FAQs: {e}")
        return []
  except httpx.RequestError as e:
        print(f"Request error fetching FAQs: {e}")
        return []
  
async def fetch_documents_from_api() -> List[Dict[str, Any]]:
    """Mengambil data dokumen (PDF yang sudah diparse) dari API Laravel."""
    url = f"{settings.LARAVEL_API_BASE_URL}/documents"
    timeout = httpx.Timeout(settings.LARAVEL_API_TIMEOUT)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            documents = data.get('data', data)
            processed_docs = []
            for item in documents:
                # Asumsi item memiliki 'content' dan 'id'
                content = item.get('content', '')
                if content: # Pastikan konten tidak kosong
                    processed_docs.append({
                        "page_content": content,
                        "id": item.get('id', ''), 
                        "metadata": {"source": "document", "id": item.get('id')}
                    })
            return processed_docs
    except httpx.HTTPStatusError as e:
        print(f"Error fetching Documents: {e}")
        return []
    except httpx.RequestError as e:
        print(f"Request error fetching Documents: {e}")
        return []

async def fetch_tracking_status_from_api(tracking_number: str) -> Optional[Dict[str, Any]]:
    """Mengambil status dokumen berdasarkan nomor registrasi dari API Laravel."""
    # Endpoint ini mungkin perlu dibuat di Laravel
    url = f"{settings.LARAVEL_API_BASE_URL}/tracking/{tracking_number}"

    print("Fetching tracking status from URL yeh:", url)
    timeout = httpx.Timeout(settings.LARAVEL_API_TIMEOUT, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=headers)
            print("Response tracking number:", response)
            response.raise_for_status()
            data = response.json()
            print("Data tracking number:", data)
            # Asumsi API mengembalikan data status
            return data.get('data', data)
    except httpx.HTTPStatusError as e:
        print(f"Error fetching Tracking Status for {tracking_number}: {e}")
        return None
    except httpx.RequestError as e:
        print(f"Request error fetching Tracking Status for {tracking_number}: {e}")
        return None
    
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