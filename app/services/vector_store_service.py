import asyncio
import logging
from typing import List
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
from app.services.api_client import fetch_faqs_from_api, fetch_documents_from_api
from app.services.embedding_service import get_embeddings_model

logger = logging.getLogger(__name__)

# Variabel global untuk menyimpan vector store dan retriever
# Ini akan diinisialisasi oleh initialize_vector_store
_vector_store = None
_retriever = None

async def _fetch_all_data_from_apis() -> List[Document]:
    """Mengambil semua data dari API Laravel dan mengonversinya ke dokumen LangChain."""
    logger.info("Fetching data from Laravel APIs...")
    faq_docs_raw = await fetch_faqs_from_api()
    doc_docs_raw = await fetch_documents_from_api()

    all_docs_raw = faq_docs_raw + doc_docs_raw

    if not all_docs_raw:
        logger.warning("No data fetched from APIs. Vector store might be empty.")
        return []

    # Konversi ke format Document LangChain
    documents = [Document(page_content=d['page_content'], metadata=d['metadata']) for d in all_docs_raw]
    logger.info(f"Successfully fetched {len(documents)} raw documents from APIs.")
    return documents

def _split_documents(documents: List[Document]) -> List[Document]:
    """Memecah dokumen menjadi potongan-potongan (chunks) yang lebih kecil."""
    logger.info("Splitting documents...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=300,
    )
    # --- Tambahkan preprocessing di sini ---
    # Misalnya, jika Anda ingin lowercase semua chunk sebelum disimpan
    processed_docs = []
    for doc in documents:
        # Gunakan fungsi preprocess dari helpers
        from app.utils.helpers import preprocess_question # Impor lokal untuk menghindari circular import jika perlu
        processed_content = preprocess_question(doc.page_content) # Asumsikan preprocess_question hanya mengembalikan string yang diproses
        processed_docs.append(Document(page_content=processed_content, metadata=doc.metadata))
    # ---
    splits = text_splitter.split_documents(processed_docs) # Gunakan dokumen yang telah diproses
    logger.info(f"Documents split into {len(splits)} chunks.")
    return splits



async def initialize_vector_store(force_refresh: bool = False):
    """
    force_refresh=True: Always rebuild from API
    force_refresh=False: Use cached data jika ada (default)
    """
    global _vector_store, _retriever
    
    embeddings = get_embeddings_model()
    
    # Coba load existing store jika tidak force refresh
    if not force_refresh:
        try:
            existing_store = Chroma(
                collection_name=settings.CHROMA_COLLECTION_NAME,
                embedding_function=embeddings,
                persist_directory=settings.CHROMA_PERSIST_DIR,
            )
            existing_count = existing_store._collection.count()
            if existing_count > 0:
                logger.info(f"Loaded existing vector store with {existing_count} documents.")
                _vector_store = existing_store
                _retriever = _vector_store.as_retriever(search_kwargs={"k": 3})
                return _vector_store
        except Exception as e:
            logger.warning(f"Could not load existing store: {e}")
    
    # Jika tidak ada cached data atau force_refresh=True, rebuild dari API
    logger.info("Rebuilding vector store from API...")
    raw_documents = await _fetch_all_data_from_apis()
    splits = _split_documents(raw_documents) if raw_documents else []
    
    if splits:
        _vector_store = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            collection_name=settings.CHROMA_COLLECTION_NAME,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
        logger.info("New vector store created from API data.")
    else:
        _vector_store = Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
        logger.info("Created empty vector store.")
    
    _retriever = _vector_store.as_retriever(search_kwargs={"k": 3})
    return _vector_store

def get_retriever():
    """
    Mengembalikan retriever yang telah diinisialisasi oleh initialize_vector_store.
    Pastikan initialize_vector_store telah dipanggil sebelum menggunakan fungsi ini.
    """
    if _retriever is None:
        logger.error("Retriever is not initialized. Call initialize_vector_store first.")
        raise RuntimeError("Retriever is not initialized. Call initialize_vector_store first.")
    return _retriever

# Fungsi opsional untuk memperbarui data jika diperlukan tanpa restart aplikasi
async def refresh_vector_store_data():
    """
    Fungsi untuk memperbarui vector store dengan data terbaru dari API.
    Ini bisa dipanggil melalui endpoint API atau proses internal.
    """
    global _vector_store, _retriever
    logger.info("Refreshing vector store data...")
    # Panggil ulang inisialisasi
    await initialize_vector_store(force_refresh=True)
    # initialize_vector_store sudah memperbarui _vector_store dan _retriever secara global
    logger.info("Vector store data refreshed.")

# Fungsi opsional untuk mendapatkan instance vector store (jika diperlukan)
def get_vector_store():
    """
    Mengembalikan vector store yang telah diinisialisasi oleh initialize_vector_store.
    Pastikan initialize_vector_store telah dipanggil sebelum menggunakan fungsi ini.
    """
    if _vector_store is None:
        logger.error("Vector store is not initialized. Call initialize_vector_store first.")
        raise RuntimeError("Vector store is not initialized. Call initialize_vector_store first.")
    return _vector_store