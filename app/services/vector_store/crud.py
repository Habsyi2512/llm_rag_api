# app/services/vector_store/crud.py

import logging
from typing import List, Iterable
from app.services.vector_store.base import get_state, retry_async

logger = logging.getLogger(__name__)

async def _upsert_documents_in_store(docs: Iterable, batch_size: int = 10) -> None:
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

async def delete_documents_by_metadata(metadata_key: str, metadata_value: str):
    """
    Delete all vectors that have metadata[metadata_key] == metadata_value
    """
    state = get_state()
    chroma = state.vector_store
    if chroma is None:
        raise RuntimeError("Vector store is not initialized")

    try:
        delete_fn = getattr(chroma, "delete", None)
        if delete_fn:
            maybe_coro = delete_fn(ids=None, where={metadata_key: metadata_value})
            if hasattr(maybe_coro, "__await__"):
                await maybe_coro
            return {"status": "deleted", metadata_key: metadata_value}
        else:
            coll = chroma
            def sync_query_delete():
                matches = coll.query(filter={metadata_key: metadata_value})
                ids = [m["id"] for m in matches] if matches else []
                if ids:
                    coll.delete(ids=ids)
                return len(ids)
            import asyncio
            loop = asyncio.get_running_loop()
            deleted_count = await loop.run_in_executor(None, sync_query_delete)
            return {"status": "deleted", metadata_key: metadata_value, "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Error deleting documents by {metadata_key}={metadata_value}: {e}")
        raise

async def update_documents_by_metadata(metadata_key: str, metadata_value: str, new_documents):
    """
    Strategy: delete old docs for metadata_key=metadata_value then upsert new chunks
    """
    # Langkah 1: Hapus dokumen lama
    await delete_documents_by_metadata(metadata_key, metadata_value)
    
    # Langkah 2: Tambahkan dokumen baru
    await add_documents(new_documents)
    
    return {"status": "updated", metadata_key: metadata_value}