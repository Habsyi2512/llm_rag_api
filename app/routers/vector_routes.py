from fastapi import APIRouter, HTTPException, Security, Body
from app.auth import verify_api_key
from app.services.vector_store.service import (
    refresh_vector_store_data,
    get_retriever,
    add_faq_to_vector_store,
    update_faq_in_vector_store,
    delete_faq_from_vector_store
)
from app.chains.conversation_chain import create_conversation_graph
from app.core.startup import set_graph

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
