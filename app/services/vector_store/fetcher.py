# app/services/vector_store/fetcher.py
import logging
from typing import List, Dict, Any, Optional
from app.core.database import AsyncSessionLocal
from app.models.domain import Faq, Document, DocumentTracking
from sqlalchemy.future import select

logger = logging.getLogger(__name__)

async def fetch_all_faqs() -> Dict[str, List[Dict[str, Any]]]:
    """Fetch FAQs dari local database"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Faq))
            faqs = result.scalars().all()
            
            data = []
            for faq in faqs:
                data.append({
                    "id": faq.id,
                    "question": faq.question,
                    "answer": faq.answer
                })
            logger.info(f"✅ Fetched {len(data)} FAQs from DB")
            return {"data": data}
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching FAQs: {e}")
        return {"data": []}

async def fetch_all_documents() -> Dict[str, List[Dict[str, Any]]]:
    """Fetch documents dari local database"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Document))
            docs = result.scalars().all()
            
            data = []
            for doc in docs:
                data.append({
                    "id": doc.id,
                    "title": doc.title,
                    "source_path": doc.source_path,
                    "content": doc.content,
                    "metadata": doc.metadata_json
                })
            logger.info(f"✅ Fetched {len(data)} documents from DB")
            return {"data": data}
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching documents: {e}")
        return {"data": []}

async def fetch_tracking_status_from_api(tracking_number: str) -> Optional[Dict[str, Any]]:
    """Fetch tracking status by registration number from DB."""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(DocumentTracking).where(DocumentTracking.tracking_number == tracking_number))
            tracking = result.scalars().first()
            if tracking:
                logger.info(f"✅ Tracking data found for {tracking_number}")
                return {
                    "id": tracking.id,
                    "tracking_number": tracking.tracking_number,
                    "document_type": tracking.document_type,
                    "status": tracking.status,
                    "note": tracking.note,
                    "estimated_completion_date": str(tracking.estimated_completion_date) if tracking.estimated_completion_date else None,
                    "completed_at": str(tracking.completed_at) if tracking.completed_at else None
                }
            return None
    except Exception as e:
        logger.error(f"❌ Unexpected error tracking {tracking_number}: {e}")
        return None

# Backward compatibility
fetch_faqs_from_api = fetch_all_faqs
fetch_documents_from_api = fetch_all_documents