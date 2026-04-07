import os
import secrets
from fastapi import APIRouter, Depends, HTTPException, Security, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete, update, func
from typing import List
from datetime import datetime
from app.models.domain import now_wib

from app.core.database import get_db
from app.core.auth import get_current_admin
from app.models.domain import Faq, Document, DocumentTracking, ChatHistory, User, ChatMessage, ChatSession
from app.schemas.dashboard import (
    FaqCreate, FaqUpdate, FaqResponse,
    DocumentCreate, DocumentUpdate, DocumentResponse,
    DocumentTrackingCreate, DocumentTrackingUpdate, DocumentTrackingResponse,
    ChatHistoryCreate, ChatHistoryResponse
)
from app.services.vector_store.vector_store_service import (
    add_faq_to_vector_store,
    update_faq_in_vector_store,
    delete_faq_from_vector_store,
    add_document_to_vector_store,
    update_document_in_vector_store,
    delete_document_from_vector_store
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard CMS"])

# ==========================================
# FAQs CRUD
# ==========================================

@router.get("/faqs")
async def get_faqs(page: int = 1, search: str = "", db: AsyncSession = Depends(get_db)):
    query = select(Faq)
    if search:
        query = query.where(Faq.question.ilike(f"%{search}%") | Faq.answer.ilike(f"%{search}%"))
    
    # Simple pagination
    per_page = 10
    offset = (page - 1) * per_page
    
    # Get total count
    count_query = select(Faq.id)
    if search:
        count_query = count_query.where(Faq.question.ilike(f"%{search}%") | Faq.answer.ilike(f"%{search}%"))
    
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())
    
    # Get paginated data
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    items = result.scalars().all()
    
    last_page = (total + per_page - 1) // per_page if total > 0 else 1
    
    # Return Laravel-like structure
    return {
        "data": [FaqResponse.model_validate(item).model_dump() for item in items],
        "current_page": page,
        "last_page": last_page,
        "total": total
    }

@router.post("/faqs", response_model=FaqResponse)
async def create_faq(faq: FaqCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    new_faq = Faq(**faq.model_dump())
    db.add(new_faq)
    await db.commit()
    await db.refresh(new_faq)
    
    # Sync with Vector Store
    content = f"Q: {new_faq.question}\nA: {new_faq.answer}"
    background_tasks.add_task(
        add_faq_to_vector_store,
        content=content,
        metadata={"faq_id": str(new_faq.id), "type": "faq"}
    )
    
    return new_faq

@router.get("/faqs/{faq_id}", response_model=FaqResponse)
async def get_faq(faq_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Faq).where(Faq.id == faq_id))
    faq = result.scalars().first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return faq

@router.put("/faqs/{faq_id}", response_model=FaqResponse)
async def update_faq(faq_id: int, faq: FaqUpdate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Faq).where(Faq.id == faq_id))
    db_faq = result.scalars().first()
    if not db_faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    
    for key, value in faq.model_dump().items():
        setattr(db_faq, key, value)
    
    db_faq.updated_at = now_wib()
    await db.commit()
    await db.refresh(db_faq)
    
    # Sync with Vector Store
    content = f"Q: {db_faq.question}\nA: {db_faq.answer}"
    background_tasks.add_task(
        update_faq_in_vector_store,
        faq_id=str(db_faq.id),
        content=content,
        metadata={"faq_id": str(db_faq.id), "type": "faq"}
    )
    
    return db_faq

@router.delete("/faqs/{faq_id}")
async def delete_faq(faq_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Faq).where(Faq.id == faq_id))
    faq = result.scalars().first()
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    
    await db.delete(faq)
    await db.commit()
    
    # Sync with Vector Store
    background_tasks.add_task(
        delete_faq_from_vector_store,
        faq_id=str(faq_id)
    )
    
    return {"message": "FAQ deleted successfully"}


# ==========================================
# Documents CRUD
# ==========================================

@router.get("/documents")
async def get_documents(page: int = 1, search: str = "", db: AsyncSession = Depends(get_db)):
    query = select(Document)
    if search:
        query = query.where(Document.title.ilike(f"%{search}%") | Document.content.ilike(f"%{search}%"))
    
    per_page = 10
    offset = (page - 1) * per_page
    
    count_query = select(Document.id)
    if search:
        count_query = count_query.where(Document.title.ilike(f"%{search}%") | Document.content.ilike(f"%{search}%"))
    
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())
    
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    items = result.scalars().all()
    
    last_page = (total + per_page - 1) // per_page if total > 0 else 1
    
    return {
        "data": [DocumentResponse.model_validate(item).model_dump() for item in items],
        "current_page": page,
        "last_page": last_page,
        "total": total
    }

@router.post("/documents")
async def create_document(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    safe_filename = file.filename.replace(" ", "_").replace("/", "").replace("\\", "")
    file_name = f"{secrets.token_hex(6)}_{safe_filename}"
    file_path = os.path.join(upload_dir, file_name)
    
    content_bytes = await file.read()
    with open(file_path, "wb") as buffer:
        buffer.write(content_bytes)
    
    new_doc = Document(
        title=title,
        source_path=file_path,
        content="File PDF Uploaded (Local Content)", 
        metadata_json={
            "size": len(content_bytes),
            "original_name": file.filename
        }
    )
    db.add(new_doc)
    await db.commit()
    await db.refresh(new_doc)
    
    # Sync with Vector Store
    background_tasks.add_task(
        add_document_to_vector_store,
        pdf_url=file_path, 
        metadata={"doc_id": str(new_doc.id), "type": "document", "title": new_doc.title}
    )
    
    return DocumentResponse.model_validate(new_doc).model_dump()

@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.put("/documents/{doc_id}", response_model=DocumentResponse)
async def update_document(doc_id: int, doc: DocumentUpdate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    db_doc = result.scalars().first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    for key, value in doc.model_dump().items():
        setattr(db_doc, key, value)
    
    db_doc.updated_at = now_wib()
    await db.commit()
    await db.refresh(db_doc)
    
    # Sync with Vector Store
    background_tasks.add_task(
        update_document_in_vector_store,
        doc_id=str(db_doc.id),
        pdf_url=db_doc.source_path,
        metadata={"doc_id": str(db_doc.id), "type": "document", "title": db_doc.title}
    )
    
    return db_doc

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Try to remove the file from the local filesystem
    if os.path.exists(doc.source_path):
        try:
            os.remove(doc.source_path)
        except Exception as e:
            print(f"Failed to delete file {doc.source_path}: {e}")
            
    await db.delete(doc)
    await db.commit()
    
    # Sync with Vector Store
    background_tasks.add_task(
        delete_document_from_vector_store,
        doc_id=str(doc_id)
    )
    
    return {"message": "Document deleted successfully"}


# ==========================================
# Document Tracking CRUD
# ==========================================

@router.get("/document-tracking")
async def get_trackings(page: int = 1, search: str = "", db: AsyncSession = Depends(get_db)):
    query = select(DocumentTracking)
    if search:
        query = query.where(DocumentTracking.tracking_number.ilike(f"%{search}%") | DocumentTracking.document_type.ilike(f"%{search}%"))
    
    per_page = 10
    offset = (page - 1) * per_page
    
    count_query = select(DocumentTracking.id)
    if search:
        count_query = count_query.where(DocumentTracking.tracking_number.ilike(f"%{search}%") | DocumentTracking.document_type.ilike(f"%{search}%"))
    
    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())
    
    query = query.offset(offset).limit(per_page)
    result = await db.execute(query)
    items = result.scalars().all()
    
    last_page = (total + per_page - 1) // per_page if total > 0 else 1
    
    return {
        "data": [DocumentTrackingResponse.model_validate(item).model_dump() for item in items],
        "current_page": page,
        "last_page": last_page,
        "total": total
    }

@router.post("/document-tracking", response_model=DocumentTrackingResponse)
async def create_tracking(tracking: DocumentTrackingCreate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    new_tracking = DocumentTracking(**tracking.model_dump())
    db.add(new_tracking)
    await db.commit()
    await db.refresh(new_tracking)
    return new_tracking

@router.get("/document-tracking/{tracking_id}", response_model=DocumentTrackingResponse)
async def get_tracking(tracking_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DocumentTracking).where(DocumentTracking.id == tracking_id))
    tracking = result.scalars().first()
    if not tracking:
        raise HTTPException(status_code=404, detail="Tracking data not found")
    return tracking

@router.put("/document-tracking/{tracking_id}", response_model=DocumentTrackingResponse)
async def update_tracking(tracking_id: int, tracking: DocumentTrackingUpdate, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(DocumentTracking).where(DocumentTracking.id == tracking_id))
    db_tracking = result.scalars().first()
    if not db_tracking:
        raise HTTPException(status_code=404, detail="Tracking data not found")
    
    for key, value in tracking.model_dump().items():
        setattr(db_tracking, key, value)
    
    db_tracking.updated_at = now_wib()
    await db.commit()
    await db.refresh(db_tracking)
    return db_tracking

@router.delete("/document-tracking/{tracking_id}")
async def delete_tracking(tracking_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
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

@router.get("/dashboard-stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    faq_count = await db.scalar(select(func.count(Faq.id)))
    doc_count = await db.scalar(select(func.count(Document.id)))
    track_count = await db.scalar(select(func.count(DocumentTracking.id)))
    chat_count = await db.scalar(select(func.count(ChatMessage.id)))
    
    return {
        "faqCount": faq_count or 0,
        "documentCount": doc_count or 0,
        "trackingCount": track_count or 0,
        "chatCount": chat_count or 0,
    }

@router.get("/chat-stats")
async def get_chat_stats(
    month: int = None, 
    year: int = None, 
    db: AsyncSession = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    """
    Mengembalikan statistik jumlah pertanyaan berdasarkan kategori.
    Bisa difilter berdasarkan bulan dan tahun via query param ?month=4&year=2026.
    """
    from sqlalchemy import extract
    
    stats_map = {}

    # 1. Ambil dari ChatMessage (sistem baru) - hanya assistant messages yang memiliki category
    cm_query = (
        select(ChatMessage.category, func.count(ChatMessage.id))
        .where(ChatMessage.category.isnot(None), ChatMessage.role == "assistant")
    )
    if year:
        cm_query = cm_query.where(extract("year", ChatMessage.created_at) == year)
    if month:
        cm_query = cm_query.where(extract("month", ChatMessage.created_at) == month)
    cm_query = cm_query.group_by(ChatMessage.category)
    
    cm_result = await db.execute(cm_query)
    for category, total in cm_result.all():
        cat_name = category.strip() if category else "Umum"
        if cat_name:
            stats_map[cat_name] = stats_map.get(cat_name, 0) + total

    # 2. Ambil dari ChatHistory (sistem lama) sebagai tambahan
    ch_query = (
        select(ChatHistory.category, func.count(ChatHistory.id))
        .where(ChatHistory.category.isnot(None))
    )
    if year:
        ch_query = ch_query.where(extract("year", ChatHistory.created_at) == year)
    if month:
        ch_query = ch_query.where(extract("month", ChatHistory.created_at) == month)
    ch_query = ch_query.group_by(ChatHistory.category)
    
    ch_result = await db.execute(ch_query)
    for category, total in ch_result.all():
        cat_name = category.strip() if category else "Umum"
        if cat_name:
            stats_map[cat_name] = stats_map.get(cat_name, 0) + total

    # 3. Format response
    result = [{"category": cat, "total": count} for cat, count in stats_map.items()]
    result.sort(key=lambda x: x["total"], reverse=True)

    return result

@router.get("/chat-history", response_model=List[ChatHistoryResponse])
async def get_chat_histories(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
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
async def delete_chat_history(chat_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    result = await db.execute(select(ChatHistory).where(ChatHistory.id == chat_id))
    chat = result.scalars().first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat history not found")
    
    await db.delete(chat)
    await db.commit()
    return {"message": "Chat history deleted successfully"}


# ==========================================
# Analytics Endpoints
# ==========================================

@router.get("/chat-trend")
async def get_chat_trend(
    month: int = None, 
    year: int = None,
    db: AsyncSession = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    """Tren percakapan harian dalam periode tertentu."""
    from sqlalchemy import extract, cast, Date
    
    query = (
        select(
            cast(ChatMessage.created_at, Date).label("date"),
            func.count(ChatMessage.id).label("total")
        )
        .where(ChatMessage.role == "user")
    )
    if year:
        query = query.where(extract("year", ChatMessage.created_at) == year)
    if month:
        query = query.where(extract("month", ChatMessage.created_at) == month)
    
    query = query.group_by(cast(ChatMessage.created_at, Date)).order_by(cast(ChatMessage.created_at, Date))
    result = await db.execute(query)
    
    return [{"date": str(row.date), "total": row.total} for row in result.all()]


@router.get("/response-time-stats")
async def get_response_time_stats(
    month: int = None,
    year: int = None,
    db: AsyncSession = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    """Statistik waktu respons chatbot (avg, min, max) dan tren harian."""
    from sqlalchemy import extract, cast, Date
    
    # Base filter
    base_filter = [ChatMessage.role == "assistant", ChatMessage.response_time.isnot(None)]
    if year:
        base_filter.append(extract("year", ChatMessage.created_at) == year)
    if month:
        base_filter.append(extract("month", ChatMessage.created_at) == month)
    
    # Aggregate stats
    stats_result = await db.execute(
        select(
            func.round(func.avg(ChatMessage.response_time), 2).label("avg"),
            func.round(func.min(ChatMessage.response_time), 2).label("min"),
            func.round(func.max(ChatMessage.response_time), 2).label("max"),
            func.count(ChatMessage.id).label("count")
        ).where(*base_filter)
    )
    stats = stats_result.first()
    
    # Daily trend
    trend_result = await db.execute(
        select(
            cast(ChatMessage.created_at, Date).label("date"),
            func.round(func.avg(ChatMessage.response_time), 2).label("avg_time")
        )
        .where(*base_filter)
        .group_by(cast(ChatMessage.created_at, Date))
        .order_by(cast(ChatMessage.created_at, Date))
    )
    
    return {
        "summary": {
            "avg": float(stats.avg) if stats.avg else 0,
            "min": float(stats.min) if stats.min else 0,
            "max": float(stats.max) if stats.max else 0,
            "count": stats.count or 0
        },
        "trend": [{"date": str(row.date), "avg_time": float(row.avg_time)} for row in trend_result.all()]
    }


@router.get("/hourly-activity")
async def get_hourly_activity(
    month: int = None,
    year: int = None,
    db: AsyncSession = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    """Distribusi aktivitas chat per jam (0-23) yang diakumulasi bulanan."""
    from sqlalchemy import extract
    
    query = (
        select(
            extract("hour", ChatMessage.created_at).label("hour"),
            func.count(ChatMessage.id).label("total")
        )
        .where(ChatMessage.role == "user")
    )
    if year:
        query = query.where(extract("year", ChatMessage.created_at) == year)
    if month:
        query = query.where(extract("month", ChatMessage.created_at) == month)
    
    query = query.group_by(extract("hour", ChatMessage.created_at)).order_by(extract("hour", ChatMessage.created_at))
    result = await db.execute(query)
    
    # Fill all 24 hours
    hour_map = {int(row.hour): row.total for row in result.all()}
    return [{"hour": f"{h:02d}:00", "total": hour_map.get(h, 0)} for h in range(24)]


@router.get("/user-demographics")
async def get_user_demographics(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Distribusi pengguna berdasarkan asal desa."""
    result = await db.execute(
        select(
            func.coalesce(User.asal_desa, "Tidak Diketahui").label("desa"),
            func.count(User.id).label("total")
        )
        .where(User.role == "user")
        .group_by(User.asal_desa)
        .order_by(func.count(User.id).desc())
    )
    return [{"desa": row.desa, "total": row.total} for row in result.all()]


@router.get("/top-questions")
async def get_top_questions(
    limit: int = 10,
    month: int = None,
    year: int = None,
    db: AsyncSession = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    """Top pertanyaan paling sering ditanyakan pengguna."""
    from sqlalchemy import extract
    
    query = (
        select(
            ChatMessage.content.label("question"),
            func.count(ChatMessage.id).label("total")
        )
        .where(ChatMessage.role == "user")
    )
    if year:
        query = query.where(extract("year", ChatMessage.created_at) == year)
    if month:
        query = query.where(extract("month", ChatMessage.created_at) == month)
    
    query = (
        query.group_by(ChatMessage.content)
        .order_by(func.count(ChatMessage.id).desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return [{"question": row.question, "total": row.total} for row in result.all()]


@router.get("/tracking-status")
async def get_tracking_status(db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Distribusi status pelacakan dokumen."""
    # By status
    status_result = await db.execute(
        select(
            DocumentTracking.status.label("status"),
            func.count(DocumentTracking.id).label("total")
        )
        .group_by(DocumentTracking.status)
        .order_by(func.count(DocumentTracking.id).desc())
    )
    
    # By document type
    type_result = await db.execute(
        select(
            DocumentTracking.document_type.label("type"),
            func.count(DocumentTracking.id).label("total")
        )
        .group_by(DocumentTracking.document_type)
        .order_by(func.count(DocumentTracking.id).desc())
    )
    
    return {
        "by_status": [{"status": row.status, "total": row.total} for row in status_result.all()],
        "by_type": [{"type": row.type, "total": row.total} for row in type_result.all()]
    }


@router.get("/user-growth")
async def get_user_growth(
    month: int = None,
    year: int = None,
    db: AsyncSession = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    """Pertumbuhan pengguna baru dari waktu ke waktu (kumulatif)."""
    from sqlalchemy import cast, Date, extract
    
    query = (
        select(
            cast(User.created_at, Date).label("date"),
            func.count(User.id).label("new_users")
        )
        .where(User.role == "user")
    )
    if year:
        query = query.where(extract("year", User.created_at) == year)
    if month:
        query = query.where(extract("month", User.created_at) == month)

    query = (
        query.group_by(cast(User.created_at, Date))
        .order_by(cast(User.created_at, Date))
    )
    
    result = await db.execute(query)
    
    rows = result.all()
    cumulative = 0
    data = []
    for row in rows:
        cumulative += row.new_users
        data.append({"date": str(row.date), "new_users": row.new_users, "total_users": cumulative})
    
    return data

