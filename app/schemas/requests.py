from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None # ID unik pengguna atau sesi

class ChatResponse(BaseModel):
    response: str
    intent: str
    tracking_data: Optional[dict] = None

class FaqRequest(BaseModel):
    id: int
    question: str
    answer: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None