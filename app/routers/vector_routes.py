# app/routers/vector_routes.py

from fastapi import APIRouter, HTTPException, Security, Body
from app.auth import verify_api_key
from app.services.vector_store.service import (
    refresh_vector_store_data,
    get_retriever,
    add_faq_to_vector_store,
    update_faq_in_vector_store,
    delete_faq_from_vector_store,
    add_document_to_vector_store,
    update_document_in_vector_store,
    delete_document_from_vector_store
)
from app.chains.conversation_chain import create_conversation_graph
from app.core.startup import set_graph
from app.schemas.document import CreateDocumentPayload, UpdateDocumentPayload

import logging
router = APIRouter(prefix="/vector-store", tags=["Vector Store"])
logger = logging.getLogger(__name__)

@router.post("/refresh")
async def refresh_data(api_key: str = Security(verify_api_key)):
    """
    Refresh vector store & rebuild graph
    """
    try:
        await refresh_vector_store_data()
        retriever = get_retriever()
        new_graph = create_conversation_graph(retriever)
        set_graph(new_graph)  # Update global reference
        logger.info("Graph refreshed successfully.")
        return {"message": "Data and graph refreshed successfully"}
    except Exception as e:
        logger.error(f"Error refreshing data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/faqs")
async def create_faq(payload: dict = Body(...), api_key: str = Security(verify_api_key)):
    content = payload.get("content")
    metadata = payload.get("metadata", {})
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    try:
        return await add_faq_to_vector_store(content, metadata)
    except Exception as e:
        logger.error(f"Error adding FAQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/faqs/{faq_id}")
async def update_faq(faq_id: str, payload: dict = Body(...), api_key: str = Security(verify_api_key)):
    content = payload.get("content")
    metadata = payload.get("metadata", None)
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    try:
        return await update_faq_in_vector_store(faq_id, content, metadata)
    except Exception as e:
        logger.error(f"Error updating FAQ {faq_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/faqs/{faq_id}")
async def delete_faq(faq_id: str, api_key: str = Security(verify_api_key)):
    try:
        return await delete_faq_from_vector_store(faq_id)
    except Exception as e:
        logger.error(f"Error deleting FAQ {faq_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    



# =========================================================
# endpoint untuk CRUD dokumen berdasarkan doc_id
# =========================================================

@router.post("/documents")
async def create_document(payload: CreateDocumentPayload, api_key: str = Security(verify_api_key)):
    """
    Add a new Document (PDF/Text content) to the vector store.
    Metadata must contain 'doc_id' as the unique identifier.
    """
    doc_id = payload.metadata.doc_id
    pdf_url = payload.source_path
    metadata = payload.metadata.model_dump()
    if not doc_id:
        raise HTTPException(status_code=400, detail="Metadata must contain a unique 'doc_id'")

    try:
        # Menggunakan fungsi layanan dokumen yang baru
        return await add_document_to_vector_store(pdf_url=pdf_url, metadata=metadata)
    except Exception as e:
        logger.error(f"Error adding Document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Pastikan Anda mengimpor ProcessDocumentPayload dan _download_pdf_and_get_chunks

# Ganti 'payload: dict = Body(...)' dengan Model Pydantic yang benar
@router.put("/documents/{doc_id}")
async def update_document(
    doc_id: str, 
    payload: UpdateDocumentPayload, 
    api_key: str = Security(verify_api_key)
):
    """
    Update an existing Document by doc_id. 
    Menghapus chunks lama lalu memproses dan meng-upsert PDF baru.
    """
    pdf_url = payload.source_path
    metadata = payload.metadata.model_dump(exclude_none=True) if payload.metadata else {}

    if not pdf_url:
        raise HTTPException(status_code=400, detail="PDF URL is required for update")

    try:
        # Panggil fungsi layanan update yang akan menerima URL PDF
        # Logika pemrosesan akan dilakukan di dalam update_document_in_vector_store
        return await update_document_in_vector_store(doc_id, pdf_url, metadata)
    except RuntimeError as e:
        logger.error(f"Runtime error during PDF update for doc {doc_id}: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating Document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error during update.")
    

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, api_key: str = Security(verify_api_key)):
    """
    Delete all chunks associated with the given doc_id.
    """
    try:
        # Menggunakan fungsi layanan dokumen yang baru
        return await delete_document_from_vector_store(doc_id)
    except Exception as e:
        logger.error(f"Error deleting Document {doc_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
