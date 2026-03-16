from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class ChatMessageBase(BaseModel):
    role: str
    content: str
    retrieved_docs: Optional[Any] = None
    response_time: Optional[float] = None

class ChatMessageResponse(ChatMessageBase):
    id: int
    session_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionBase(BaseModel):
    title: Optional[str] = None

class ChatSessionResponse(ChatSessionBase):
    id: str
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChatSessionWithMessages(ChatSessionResponse):
    messages: List[ChatMessageResponse] = []

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None # If None, create new session
