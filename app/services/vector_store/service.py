# app/services/vector_store/service.py
import logging, asyncio, inspect, tempfile, httpx, os
from typing import Optional, Dict, Any, Callable, List
from langchain_community.document_loaders import PyMuPDFLoader
from app.services.vector_store.base import get_state
from app.services.vector_store.fetcher import fetch_all_faqs, fetch_all_documents
from app.services.vector_store.splitter import split_documents_to_chunks
from app.services.vector_store.crud import (
    add_documents as crud_add_documents,
    delete_documents_by_faq_id,
    update_documents_by_faq_id,
    delete_documents_by_doc_id,
    update_documents_by_doc_id
)
from app.services.api_client import download_file_to_temp
from app.services.embedding_service import get_embeddings_model
from app.core.config import settings

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
    result = fn(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return await asyncio.to_thread(lambda: result)

async def _download_pdf_and_get_chunks(pdf_url: str, metadata: Dict) -> List:
    """Mengunduh PDF secara temporer, mengekstrak teks, dan memecah menjadi chunks."""
    temp_path = None
    
    try:
        # 1. Download PDF ke file temporer
        temp_path = await download_file_to_temp(pdf_url, suffix=".pdf")
        
        # 2. Load Dokumen menggunakan PyMuPDFLoader (lebih baik menangani spasi/font)
        def sync_load_pdf():
            loader = PyMuPDFLoader(temp_path)
            return loader.load()  

        documents = await asyncio.to_thread(sync_load_pdf)

        full_text = ""
        for doc in documents:
            full_text += doc.page_content + "\n"

        combined = [{
            "content" : full_text,
            "metadata": dict(metadata)
        }]

        # 4. Split ke chunks (menggunakan fungsi yang sudah ada)
        chunks = split_documents_to_chunks(combined)
        return chunks

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP Error {e.response.status_code} accessing PDF: {pdf_url}")
        raise RuntimeError(f"Gagal mengunduh PDF: {e}")
    except Exception as e:
        logger.exception(f"Error processing PDF from {pdf_url}: {e}")
        raise RuntimeError(f"Gagal memproses PDF: {e}")
    finally:
        # 5. Bersihkan file temporer
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


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

    persist_directory = persist_directory or settings.CHROMA_PERSIST_DIR
    collection_name = collection_name or settings.CHROMA_COLLECTION_NAME

    def _sync_create():
        try:
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
            raise

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
    async with state.lock:
        if state.initialized and not force_refresh:
            logger.info("Vector store already initialized and force_refresh=False -> skip")
            return

        logger.info("Initializing embeddings model...")
        print("mulai menjalankan embeddings...")
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

    combined_full_docs = []    # Dokumen FAQ yang masih perlu di-split
    pdf_processing_tasks = []  # List tasks untuk PDF (akan menghasilkan chunks)

    # 1. Normalize FAQs (Masih menggunakan content string dan akan di-split nanti)
    for f in faqs:
        question = f.get("question", "").strip()
        answer = f.get("answer", "").strip()
        content = f"pertanyaan: {question}\njawaban: {answer}".strip()
        
        if content:
            combined_full_docs.append({
                "content": content,
                "metadata": {
                    "source": "faq",
                    "faq_id": str(f.get("id", "")),
                }
            })

    # 2. Siapkan Tasks Pemrosesan Dokumen PDF (Konkuren)
    for d in docs:
        # Asumsi source_path berisi URL publik yang dikirim dari Laravel
        pdf_url = d.get("source_path", "").strip() 
        doc_id = str(d.get("id", ""))
        title = d.get("title", "")
        
        if pdf_url:
            metadata = {
                "source": "document",
                "title": title,
                "doc_id": doc_id,
            }
            # Buat task untuk mengunduh, mengekstrak, dan memecah PDF
            task = _download_pdf_and_get_chunks(pdf_url, metadata)
            pdf_processing_tasks.append(task)
        else:
            logger.warning(f"Document ID {doc_id} skipped: No source_path found.")

    # 3. Eksekusi semua tugas PDF secara Konkuren
    logger.info(f"🚀 Starting concurrent PDF processing for {len(pdf_processing_tasks)} documents...")
    
    # asyncio.gather mengembalikan list of lists of chunks (atau Exception jika gagal)
    list_of_chunks = await asyncio.gather(*pdf_processing_tasks, return_exceptions=True) 

    # 4. Gabungkan dan filter hasil PDF
    processed_chunks = []
    for result in list_of_chunks:
        if isinstance(result, Exception):
            # Log error agar tidak menghentikan proses refresh total
            logger.error(f"❌ Failed to process one PDF document: {result}")
        else:
            # Hasilnya adalah list of chunks (list of dicts) dari satu dokumen
            processed_chunks.extend(result)

    # 5. Split Dokumen FAQ yang tersisa
    faq_chunks = split_documents_to_chunks(combined_full_docs)
    
    # 6. Gabungkan semua chunks (FAQ + PDF)
    final_chunks = faq_chunks + processed_chunks
    
    # Lanjutkan dengan final_chunks
    if not final_chunks:
        logger.warning("⚠️ No data")
        return {"status": "no_data"}

    # Clear collection - JANGAN delete_collection, pakai delete dengan where={}
    chroma = state.vector_store
    # ... (Logika clearing collection tetap sama, menggunakan final_chunks. Tidak ditampilkan di sini)
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
    logger.info(f"📤 Upserting {len(final_chunks)} chunks...")
    await crud_add_documents(final_chunks)

    # Recreate retriever
    state.retriever = chroma.as_retriever()
    
    logger.info(f"✅ Indexed {len(final_chunks)} chunks")
    return {"status": "ok", "items_indexed": len(final_chunks)}



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



async def add_document_to_vector_store(pdf_url: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Mengunduh PDF dari URL, mengekstrak, memecah, dan meng-upsert chunks.
    """
    state = get_state()
    if not state.initialized:
        raise RuntimeError("Vector store not initialized")

    metadata = metadata or {}
    if "doc_id" not in metadata:
        logger.warning("add_document_to_vector_store called without doc_id in metadata")

    # Ambil chunks dari proses download dan ekstraksi
    chunks = await _download_pdf_and_get_chunks(pdf_url, metadata)
    
    if not chunks:
        logger.warning(f"No text extracted from PDF: {pdf_url}")
        return {"status": "no_content", "indexed_chunks": 0}

    # Upsert chunks yang sudah diekstrak
    await maybe_async_call(crud_add_documents, chunks)
    
    return {"status": "ok", "indexed_chunks": len(chunks)}


# ... (Pastikan _download_pdf_and_get_chunks tersedia)

async def update_document_in_vector_store(doc_id: str, pdf_url: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Update: Hapus chunks lama berdasarkan doc_id, lalu unduh, ekstrak PDF baru, dan upsert.
    """
    state = get_state()
    if not state.initialized:
        raise RuntimeError("Vector store not initialized")

    metadata = metadata or {}
    
    # 1. UNDUH, EKSTRAK, DAN SPLIT PDF BARU
    logger.info(f"Processing new PDF content for doc_id: {doc_id}")
    try:
        # Gunakan fungsi yang modular
        new_documents_chunks = await _download_pdf_and_get_chunks(pdf_url, metadata)
    except Exception as e:
        # Angkat error, jangan lanjutkan jika pemrosesan PDF baru gagal
        raise RuntimeError(f"Gagal memproses PDF baru untuk update: {e}")

    if not new_documents_chunks:
        # Jika PDF kosong atau gagal diekstrak, hapus dokumen lama dan kembalikan status.
        await maybe_async_call(delete_documents_by_doc_id, doc_id)
        return {"status": "cleared", "message": "New PDF content was empty, old document deleted.", "doc_id": doc_id}

    # 2. DELETE OLD, UPSERT NEW (Menggunakan CRUD yang modular)
    # update_documents_by_doc_id menangani DELETE kemudian ADD
    return await maybe_async_call(update_documents_by_doc_id, doc_id, new_documents_chunks)


async def delete_document_from_vector_store(doc_id: str) -> Dict[str, Any]:
    """
    Delete all documents associated with doc_id.
    """
    state = get_state()
    if not state.initialized:
        raise RuntimeError("Vector store not initialized")

    return await maybe_async_call(delete_documents_by_doc_id, doc_id)

