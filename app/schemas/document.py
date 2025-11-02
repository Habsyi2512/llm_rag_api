# app/schemas/document.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class DocumentMetadata(BaseModel):
  """
    Model untuk metadata yang akan disimpan bersama dokumen di vector store.
  """
  doc_id: str = Field(..., description="ID unik dari dokumen sumber")
  source: str = Field(None, desctription="Sumber dokumen, misal: 'document', 'faq', dll.")  
  title: Optional[str] = Field(None, description="Judul dokumen atau nama file")

# Model Payload utama
class CreateDocumentPayload(BaseModel):
  """
    Model Pydantic untuk payload POST /vector-store/documents
  """
  source_path: str = Field(None, description="Path atau URL sumber dokumen")
  metadata: DocumentMetadata = Field(..., desctiption="Metadata terkait dokumen.")

  # contoh data
  class Config:
    json_schema_extra = {
            "example": {
                "content": "Ini adalah contoh konten dokumen panjang yang akan dipecah menjadi chunk.\n Penulis: John Doe.",
                "metadata": {
                    "doc_id": "DOK-001",
                    "source": "document",
                    "title": "Pedoman Penggunaan"
                }
            }
        }
    
class UpdateDocumentPayload(CreateDocumentPayload):
  pass