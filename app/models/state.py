from typing import List, Optional
from langchain_core.documents import Document
from typing_extensions import TypedDict

class State(TypedDict):
    question: str
    context: List[Document]
    answer: str

    # --- Untuk percakapan ---
    conversation_history: List[str] # Riwayat percakapan
    user_id: Optional[str]          # ID sesi pengguna
    
    # --- Untuk pelacakan dokumen ---
    intent: str                     # 'general', 'tracking'
    tracking_number: Optional[str]  # Nomor registrasi jika intent tracking
    tracking_data: Optional[dict]   # Data status dari API Laravel
    category: Optional[str]         # Kategori pertanyaan (KTP, KK, dll)
