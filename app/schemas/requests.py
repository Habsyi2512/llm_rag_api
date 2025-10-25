from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None # ID unik pengguna atau sesi

class ChatResponse(BaseModel):
    response: str
    intent: str
    tracking_data: Optional[dict] = None