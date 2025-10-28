# app/services/vector_store/service.py
import logging
import asyncio
import inspect
from typing import Optional, List, Dict, Any, Callable

from app.services.vector_store.base import get_state
from app.services.vector_store.fetcher import fetch_all_faqs, fetch_all_documents
from app.services.vector_store.splitter import split_documents_to_chunks
from app.services.vector_store.crud import (
    add_documents as crud_add_documents,
    delete_documents_by_faq_id,
    update_documents_by_faq_id,
)
from app.services.embedding_service import get_embeddings_model
from app.core.config import settings

# langchain_chroma import depends on your environment; keep try/except
try:
    from langchain_chroma import Chroma
except Exception:
    Chroma = None

logger = logging.getLogger(__name__)
BATCH_SIZE = 64


async def maybe_async_call(fn: Callable, *args, **kwargs):
    """
    Call `fn` whether it's sync or async. If sync, run in threadpool with to_thread.
    If async, await it.
    Returns the function result.
    """
    if asyncio.iscoroutinefunction(fn):
        return await fn(*args, **kwargs)
    # if it's a callable but returns an awaitable (rare), handle that too
    result = fn(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    # sync result
    return await asyncio.to_thread(lambda: result)


async def _create_or_connect_chroma(
    embeddings,
    persist_directory: Optional[str] = None,
    collection_name: Optional[str] = None,
):
    """
    Create or connect to chroma vector store.
    This wrapper runs the potentially-blocking Chroma constructor in a thread so it
    doesn't block the event loop.
    """
    if Chroma is None:
        raise RuntimeError("Chroma client not available; ensure langchain_chroma is installed")

    # Use settings defaults if not provided
    persist_directory = persist_directory or settings.CHROMA_PERSIST_DIR
    collection_name = collection_name or settings.CHROMA_COLLECTION_NAME

    def _sync_create():
        # prefer modern kwargs; fallback to older signature
        try:
            # Optionally add client settings to avoid telemetry blocking
            try:
                chroma = Chroma(
                    embedding_function=embeddings,
                    persist_directory=persist_directory,
                    collection_name=collection_name,
                )
            except TypeError:
                chroma = Chroma(embeddings)
            return chroma
        except Exception:
            # re-raise for outer to catch
            raise

    # run sync constructor in thread
    chroma = await asyncio.to_thread(_sync_create)
    return chroma


async def initialize_vector_store(
    force_refresh: bool = False,
    persist_directory: Optional[str] = None,
    collection_name: Optional[str] = None,
) -> None:
    """
    Initialize/reuse embeddings model and Chroma client and ensure retriever available.
    This function will not deadlock because potentially-long operations (embedding init,
    chroma creation, refresh upserts) are executed outside of the critical lock or inside threads.
    """
    state = get_state()
    need_refresh = False

    # Acquire lock only for short, safe operations (setting state, connecting chroma instance reference).
    async with state.lock:
        if state.initialized and not force_refresh:
            logger.info("Vector store already initialized and force_refresh=False -> skip")
            return

        logger.info("Initializing embeddings model...")
        print("mulai menjalankan embeddings...")
        # get_embeddings_model is sync in many setups; run it in a thread
        embeddings = await asyncio.to_thread(get_embeddings_model)
        state.embeddings = embeddings
        logger.info("embedding model siap")

        logger.info("Connecting to / creating chroma client...")
        try:
            chroma = await _create_or_connect_chroma(
                embeddings, persist_directory=persist_directory, collection_name=collection_name
            )
        except Exception as e:
            logger.exception("Failed to create/connect to Chroma: %s", e)
            raise

        state.vector_store = chroma

        # determine whether we must refresh (but DO NOT call refresh while holding lock)
        if force_refresh:
            need_refresh = True
            logger.info("Force refresh requested: will rebuild from source data after lock")
        else:
            try:
                # try a few heuristics to check if chroma has data
                has_data = False
                # prefer `count()` or `_collection.count()`
                check = getattr(chroma, "count", None)
                if callable(check):
                    maybe = check()
                    if inspect.isawaitable(maybe):
                        has_data = await maybe
                    else:
                        has_data = bool(maybe)
                else:
                    # try internal collection count if available
                    inner = getattr(chroma, "_collection", None)
                    if inner is not None and hasattr(inner, "count"):
                        try:
                            c = inner.count()
                            has_data = bool(c)
                        except Exception:
                            has_data = False
                    else:
                        # fallback: try a small query if as_retriever exists
                        retr_fn = getattr(chroma, "as_retriever", None)
                        if callable(retr_fn):
                            try:
                                retr = retr_fn()
                                # try a lightweight call if retriever supports it (not guaranteed)
                                has_data = False  # fallback: if we can't determine, treat as empty
                            except Exception:
                                has_data = False

                if not has_data:
                    logger.info("Chroma empty, will populate initial dataset (outside lock)")
                    need_refresh = True
            except Exception as e:
                logger.warning("Could not detect chroma content or populate flag automatically: %s", e)
                need_refresh = True

    # Perform heavy operations (refresh) OUTSIDE lock to avoid deadlock and to keep event loop responsive.
    if need_refresh:
        logger.info("Starting vector store refresh (outside lock)...")
        # Run refresh - this function itself uses the lock for exclusive upsert operations.
        await refresh_vector_store_data()

    # After refresh (or if no refresh needed), ensure retriever is set and mark initialized
    # Note: use state.vector_store which was set inside lock above
    chroma = state.vector_store
    retriever = None
    try:
        make_retriever = getattr(chroma, "as_retriever", None)
        if make_retriever:
            # as_retriever is usually sync
            retriever = make_retriever()
        else:
            retriever = chroma
    except Exception as e:
        logger.error("Failed to create retriever: %s", e)
        retriever = chroma

    state.retriever = retriever
    state.initialized = True
    logger.info("Vector store initialized and retriever ready.")


def get_retriever():
    state = get_state()
    return state.retriever


async def refresh_vector_store_data(batch_size: int = BATCH_SIZE) -> Dict[str, Any]:
    state = get_state()
    logger.info("🔄 Starting full refresh...")

    # Fetch data
    try:
        faqs_response = await fetch_all_faqs()
        docs_response = await fetch_all_documents()
    except Exception as e:
        logger.error(f"❌ Fetch failed: {e}")
        return {"status": "error", "message": str(e)}

    # Extract arrays
    faqs = faqs_response.get("data", []) if isinstance(faqs_response, dict) else faqs_response
    docs = docs_response.get("data", []) if isinstance(docs_response, dict) else docs_response
    
    logger.info(f"📥 Fetched {len(faqs)} FAQs, {len(docs)} docs")

    combined = []

    # Normalize FAQs
    for f in faqs:
        question = f.get("question", "").strip()
        answer = f.get("answer", "").strip()
        content = f"pertanyaan: {question}\njawaban: {answer}".strip()
        
        if content:
            combined.append({
                "content": content,
                "metadata": {
                    "source": "faq",
                    "faq_id": str(f.get("id", "")),
                }
            })

    for idx, d in enumerate(docs):
        content = d.get("content", "").strip()
        print(f"Dokumen ke-{idx} dengan ID {d.get('id')} memiliki content length: {len(content)}")
        if content:
            combined.append({
                "content": content,
                "metadata": {
                    "source": "document",
                    "title": d.get("title", ""),
                    "doc_id": str(d.get("id"))
                }
            })

    print("jumlah combined:", len(combined))

    if not combined:
        logger.warning("⚠️ No data")
        return {"status": "no_data"}

    # Split chunks
    chunks = split_documents_to_chunks(combined)
    logger.info(f"✂️ Split into {len(chunks)} chunks")

    # Clear collection - JANGAN delete_collection, pakai delete dengan where={}
    chroma = state.vector_store
    try:
        # Get all IDs and delete them (safer than delete_collection)
        logger.info("🗑️ Clearing collection...")
        collection = chroma._collection
        
        # Delete all documents
        try:
            collection.delete(where={})  # Delete all with empty filter
        except:
            # Fallback: get all IDs then delete
            try:
                all_data = collection.get()
                if all_data and all_data.get('ids'):
                    collection.delete(ids=all_data['ids'])
            except Exception as e:
                logger.warning(f"⚠️ Clear fallback failed: {e}")
        
        logger.info("✅ Collection cleared")
    except Exception as e:
        logger.warning(f"⚠️ Clear failed: {e}")

    # Upsert chunks
    logger.info(f"📤 Upserting {len(chunks)} chunks...")
    await add_documents(chunks)

    # Recreate retriever
    state.retriever = chroma.as_retriever()
    
    logger.info(f"✅ Indexed {len(chunks)} chunks")
    return {"status": "ok", "items_indexed": len(chunks)}



async def add_faq_to_vector_store(content: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Add a single FAQ (content + metadata) to vector store.
    We split into chunks and then upsert.
    """
    state = get_state()
    if not state.initialized:
        raise RuntimeError("Vector store not initialized")
    
    print("menambahkan data ke vector store...")
    print(f"content:\n{content}")
    print(f"metadata:\n{metadata}")

    metadata = metadata or {}
    if "faq_id" not in metadata:
        logger.warning("add_faq_to_vector_store called without faq_id in metadata")

    docs = split_documents_to_chunks([{"content": content, "metadata": metadata}])
    # reuse add_documents CRUD (may be sync/async)
    await maybe_async_call(crud_add_documents, docs)
    return {"status": "ok", "indexed_chunks": len(docs)}


async def update_faq_in_vector_store(faq_id: str, content: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Update: delete existing docs with faq_id then upsert new chunks.
    """
    state = get_state()
    if not state.initialized:
        raise RuntimeError("Vector store not initialized")

    metadata = metadata or {}
    metadata["faq_id"] = faq_id
    docs = split_documents_to_chunks([{"content": content, "metadata": metadata}])
    return await maybe_async_call(update_documents_by_faq_id, faq_id, docs)


async def delete_faq_from_vector_store(faq_id: str) -> Dict[str, Any]:
    """
    Delete all documents associated with faq_id.
    """
    state = get_state()
    if not state.initialized:
        raise RuntimeError("Vector store not initialized")

    return await maybe_async_call(delete_documents_by_faq_id, faq_id)

async def add_documents(documents: list):
    """
    Upsert list of documents (each {'content': str, 'metadata': dict}) into Chroma vector store.
    """
    state = get_state()
    chroma = state.vector_store
    if not chroma:
        raise RuntimeError("Vector store not initialized")
    
    if not documents:
        logger.info("No documents to add")
        return

    # Langchain Chroma expects Document objects or dicts with content + metadata
    try:
        # Upsert all documents at once
        if hasattr(chroma, "add_documents"):  # LangChain Chroma method
            chroma.add_documents(documents)
        elif hasattr(chroma, "upsert"):       # ChromaDB API
            chroma.upsert(documents)
        else:
            raise RuntimeError("Chroma client does not support add_documents or upsert")
        logger.info("Added %d documents to vector store", len(documents))
    except Exception as e:
        logger.error("Failed to add documents to vector store: %s", e)
        raise
