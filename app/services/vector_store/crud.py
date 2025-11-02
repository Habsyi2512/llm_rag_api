# app/services/vector_store/crud.py

import logging
from typing import List, Iterable
from app.services.vector_store.base import get_state, retry_async

logger = logging.getLogger(__name__)

async def _upsert_documents_in_store(docs: Iterable, batch_size: int = 64) -> None:
    """
    Upsert documents into vector store in batches.
    Each document is expected to be a langchain Document with metadata.
    """
    state = get_state()
    chroma = state.vector_store
    if chroma is None:
        raise RuntimeError("Vector store is not initialized")

    batch = []
    for doc in docs:
        batch.append(doc)
        if len(batch) >= batch_size:
            logger.debug("Upserting batch size %s", len(batch))
            await _chroma_upsert(chroma, batch)
            batch = []
    if batch:
        await _chroma_upsert(chroma, batch)

async def _chroma_upsert(chroma, docs: List):
    import asyncio
    try:
        upsert = getattr(chroma, "upsert", None)
        if upsert is None:
            def sync_add():
                chroma.add_documents(docs)
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, sync_add)
        else:
            if callable(upsert):
                ret = upsert(docs) 
                if hasattr(ret, "__await__"):
                    await ret
            else:
                def sync_call():
                    upsert(docs)
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, sync_call)
    except Exception as e:
        logger.error("Error upserting to chroma: %s", e)
        raise

async def add_documents(documents):
    return await retry_async(_upsert_documents_in_store, documents, tries=3)

async def delete_documents_by_faq_id(faq_id: str):
    """
    Delete all vectors that have metadata.faq_id == faq_id
    """
    state = get_state()
    chroma = state.vector_store
    if chroma is None:
        raise RuntimeError("Vector store is not initialized")

    try:
        delete_fn = getattr(chroma, "delete", None)
        if delete_fn:
            maybe_coro = delete_fn(ids=None, where={"faq_id": faq_id})
            if hasattr(maybe_coro, "__await__"):
                await maybe_coro
            return {"status": "deleted", "faq_id": faq_id}
        else:
            coll = chroma
            def sync_query_delete():
                matches = coll.query(filter={"faq_id": faq_id})
                ids = [m["id"] for m in matches] if matches else []
                if ids:
                    coll.delete(ids=ids)
                return len(ids)
            import asyncio
            loop = asyncio.get_running_loop()
            deleted_count = await loop.run_in_executor(None, sync_query_delete)
            return {"status": "deleted", "faq_id": faq_id, "deleted_count": deleted_count}
    except Exception as e:
        logger.error("Error deleting documents from vector store: %s", e)
        raise

async def update_documents_by_faq_id(faq_id: str, new_documents):
    """
    Strategy: delete old docs for faq_id then upsert new chunks
    (atomicity depends on Chroma; we do delete then upsert)
    """
    await delete_documents_by_faq_id(faq_id)
    await add_documents(new_documents)
    return {"status": "updated", "faq_id": faq_id}

# kode baru untuk delete dan update berdasarkan doc_id 1 November 2025

# app/services/vector_store/crud.py (Asumsi implementasi Anda)

async def delete_documents_by_doc_id(doc_id: str):
    """
    Delete all vectors that have metadata.faq_id == faq_id
    """
    state = get_state()
    chroma = state.vector_store
    if chroma is None:
        raise RuntimeError("Vector store is not initialized")

    try:
        delete_fn = getattr(chroma, "delete", None)
        if delete_fn:
            maybe_coro = delete_fn(ids=None, where={"doc_id": doc_id})
            if hasattr(maybe_coro, "__await__"):
                await maybe_coro
            return {"status": "deleted", "doc_id": doc_id}
        else:
            coll = chroma
            def sync_query_delete():
                matches = coll.query(filter={"doc_id": doc_id})
                ids = [m["id"] for m in matches] if matches else []
                if ids:
                    coll.delete(ids=ids)
                return len(ids)
            import asyncio
            loop = asyncio.get_running_loop()
            deleted_count = await loop.run_in_executor(None, sync_query_delete)
            return {"status": "deleted", "doc_id": doc_id, "deleted_count": deleted_count}
    except Exception as e:
        logger.error("Error deleting documents from vector store: %s", e)
        raise

async def update_documents_by_doc_id(doc_id: str, new_documents):
    """
    Strategy: delete old docs for doc_id then upsert new chunks
    """
    # Langkah 1: Hapus dokumen lama
    await delete_documents_by_doc_id(doc_id) 
    
    # Langkah 2: Tambahkan dokumen baru
    await add_documents(new_documents) 
    
    return {"status": "updated", "faq_id": doc_id}