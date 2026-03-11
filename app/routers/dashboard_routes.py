from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, update
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.auth import verify_api_key
from app.models.domain import Faq, Document, DocumentTracking, ChatHistory
from app.schemas.dashboard import (
    FaqCreate, FaqUpdate, FaqResponse,
    DocumentCreate, DocumentUpdate, DocumentResponse,
    DocumentTrackingCreate, DocumentTrackingUpdate, DocumentTrackingResponse,
    ChatHistoryCreate, ChatHistoryResponse
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard CMS"])

# ==========================================
# FAQs CRUD
# ==========================================

@router.get("/faqs", response_model=List[FaqResponse])
async def get_faqs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Faq))
    return result.scalars().all()

@router.post("/faqs", response_model=FaqResponse)
async def create_faq(faq: FaqCreate, db: AsyncSession = Depends(get_db), api_key: str = Security(verify_api_key)):
    new_faq = Faq(**faq.model_dump())
    db.add(new_faq)
    await db.commit()
    await db.refresh(new_faq)
    return new_faq

@router.get("/faqs/{faq_id}", response_model=FaqResponse)
async def get_faq(faq_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Faq).where(Faq.id == faq_id))
    faq = result.scalars().first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return faq

@router.put("/faqs/{faq_id}", response_model=FaqResponse)
async def update_faq(faq_id: int, faq: FaqUpdate, db: AsyncSession = Depends(get_db), api_key: str = Security(verify_api_key)):
    result = await db.execute(select(Faq).where(Faq.id == faq_id))
    db_faq = result.scalars().first()
    if not db_faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    
    for key, value in faq.model_dump().items():
        setattr(db_faq, key, value)
    
    db_faq.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_faq)
    return db_faq

@router.delete("/faqs/{faq_id}")
async def delete_faq(faq_id: int, db: AsyncSession = Depends(get_db), api_key: str = Security(verify_api_key)):
    result = await db.execute(select(Faq).where(Faq.id == faq_id))
    faq = result.scalars().first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    
    await db.delete(faq)
    await db.commit()
    return {"message": "FAQ deleted successfully"}


# ==========================================
# Documents CRUD
# ==========================================

@router.get("/documents", response_model=List[DocumentResponse])
async def get_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document))
    return result.scalars().all()

@router.post("/documents", response_model=DocumentResponse)
async def create_document(doc: DocumentCreate, db: AsyncSession = Depends(get_db), api_key: str = Security(verify_api_key)):
    new_doc = Document(**doc.model_dump())
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    return new_doc

@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.put("/documents/{doc_id}", response_model=DocumentResponse)
async def update_document(doc_id: int, doc: DocumentUpdate, db: AsyncSession = Depends(get_db), api_key: str = Security(verify_api_key)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    db_doc = result.scalars().first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    for key, value in doc.model_dump().items():
        setattr(db_doc, key, value)
    
    db_doc.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_doc)
    return db_doc

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db), api_key: str = Security(verify_api_key)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await db.delete(doc)
    await db.commit()
    return {"message": "Document deleted successfully"}


# ==========================================
# Document Tracking CRUD
# ==========================================

@router.get("/trackings", response_model=List[DocumentTrackingResponse])
async def get_trackings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DocumentTracking))
    return result.scalars().all()

@router.post("/trackings", response_model=DocumentTrackingResponse)
async def create_tracking(tracking: DocumentTrackingCreate, db: AsyncSession = Depends(get_db), api_key: str = Security(verify_api_key)):
    new_tracking = DocumentTracking(**tracking.model_dump())
    db.add(new_tracking)
    await db.commit()
    await db.refresh(new_tracking)
    return new_tracking

@router.get("/trackings/{tracking_id}", response_model=DocumentTrackingResponse)
async def get_tracking(tracking_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DocumentTracking).where(DocumentTracking.id == tracking_id))
    tracking = result.scalars().first()
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking data not found")
    return tracking

@router.put("/trackings/{tracking_id}", response_model=DocumentTrackingResponse)
async def update_tracking(tracking_id: int, tracking: DocumentTrackingUpdate, db: AsyncSession = Depends(get_db), api_key: str = Security(verify_api_key)):
    result = await db.execute(select(DocumentTracking).where(DocumentTracking.id == tracking_id))
    db_tracking = result.scalars().first()
    if not db_tracking:
        raise HTTPException(status_code=404, detail="Tracking data not found")
    
    for key, value in tracking.model_dump().items():
        setattr(db_tracking, key, value)
    
    db_tracking.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(db_tracking)
    return db_tracking

@router.delete("/trackings/{tracking_id}")
async def delete_tracking(tracking_id: int, db: AsyncSession = Depends(get_db), api_key: str = Security(verify_api_key)):
    result = await db.execute(select(DocumentTracking).where(DocumentTracking.id == tracking_id))
    tracking = result.scalars().first()
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking data not found")
    
    await db.delete(tracking)
    await db.commit()
    return {"message": "Tracking data deleted successfully"}


# ==========================================
# Chat History CRUD (Optional CMS views)
# ==========================================

@router.get("/chat-history", response_model=List[ChatHistoryResponse])
async def get_chat_histories(db: AsyncSession = Depends(get_db), api_key: str = Security(verify_api_key)):
    result = await db.execute(select(ChatHistory))
    return result.scalars().all()

@router.post("/chat-history", response_model=ChatHistoryResponse)
async def create_chat_history(chat: ChatHistoryCreate, db: AsyncSession = Depends(get_db)):
    # Biarkan bisa di-post tanpa auth untuk simpan dari endpoint /chat
    new_chat = ChatHistory(**chat.model_dump())
    db.add(new_chat)
    await db.commit()
    await db.refresh(new_chat)
    return new_chat

@router.delete("/chat-history/{chat_id}")
async def delete_chat_history(chat_id: int, db: AsyncSession = Depends(get_db), api_key: str = Security(verify_api_key)):
    result = await db.execute(select(ChatHistory).where(ChatHistory.id == chat_id))
    chat = result.scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat history not found")
    
    await db.delete(chat)
    await db.commit()
    return {"message": "Chat history deleted successfully"}
