import re
from datetime import datetime

def get_time()-> str:
  return datetime.now().strftime("%Y-%m-%d %H-%M-%S")

def preprocess_question(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s\+\-\*/=]', ' ', text) # Ganti karakter non-alfanumerik dengan spasi
    text = re.sub(r'\s+', ' ', text).strip() # Gabungkan spasi berlebih
    return text

# def extract_tracking_number(text: str) -> str:
#     """Ekstrak nomor registrasi dari pesan pengguna."""
#     # Pola umum untuk nomor registrasi (bisa disesuaikan)
#     pattern = r'\b([A-Za-z0-9]{8,20})\b' # Misalnya, nomor 8-20 karakter alfanumerik
#     match = re.search(pattern, text)
#     if match:
#         return match.group(1)
#     return ""

def extract_tracking_number(text: str) -> str:
    """Ekstrak nomor registrasi dari pesan pengguna.
    Hanya mencocokkan string angka dengan panjang antara 8 dan 20 karakter.
    """
    # Pola: hanya angka, panjang antara 8 dan 20
    pattern = r'\b(\d{8,20})\b'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return ""