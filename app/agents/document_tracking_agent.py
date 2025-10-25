import re
from app.services.api_client import fetch_tracking_status_from_api
from app.utils.helpers import extract_tracking_number
from typing import Dict, Any, Optional

class DocumentTrackingAgent:
    def __init__(self):
        self.tracking_number_pattern = re.compile(r'\b([A-Za-z0-9]{8,20})\b')

    async def process_tracking_request(self, question: str, extracted_number: Optional[str] = None) -> Dict[str, Any]:
        tracking_number = extracted_number or extract_tracking_number(question)

        if not tracking_number:
            # Nomor belum diberikan, minta pengguna
            return {
                "requires_number": True,
                "message": "Untuk mengecek status dokumen, mohon berikan nomor registrasi pengurusan dokumen Anda.",
                "tracking_data": None
            }

        # Nomor diberikan, cek status
        tracking_data = await fetch_tracking_status_from_api(tracking_number)
        if tracking_data is not None:
            return {
                "requires_number": False,
                "message": f"Status dokumen dengan nomor {tracking_number}: {tracking_data.get('status', 'Informasi tidak ditemukan')}.",
                "tracking_data": tracking_data
            }
        else:
            return {
                "requires_number": False,
                "message": f"Nomor registrasi '{tracking_number}' tidak ditemukan atau statusnya tidak tersedia.",
                "tracking_data": None
            }