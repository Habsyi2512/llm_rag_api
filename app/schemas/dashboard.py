from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, date

class FaqBase(BaseModel):
    question: str
    answer: str

class FaqCreate(FaqBase):
    pass

class FaqUpdate(FaqBase):
    pass

class FaqResponse(FaqBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    title: str
    source_path: str
    content: str
    metadata_json: Optional[Dict[str, Any]] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(DocumentBase):
    pass

class DocumentResponse(DocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentTrackingBase(BaseModel):
    tracking_number: str
    document_type: str
    status: str
    note: Optional[str] = None
    estimated_completion_date: Optional[date] = None
    completed_at: Optional[datetime] = None

class DocumentTrackingCreate(DocumentTrackingBase):
    pass

class DocumentTrackingUpdate(DocumentTrackingBase):
    pass

class DocumentTrackingResponse(DocumentTrackingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryBase(BaseModel):
    message: str
    response: Optional[str] = None
    category: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class ChatHistoryCreate(ChatHistoryBase):
    pass

class ChatHistoryResponse(ChatHistoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
