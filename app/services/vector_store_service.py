import asyncio
import logging
from typing import List, Dict, Any
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
        # separators=["\n\n", "\n", " ", ""], # Default separators
    )
    splits = text_splitter.split_documents(documents)
    logger.info(f"Documents split into {len(splits)} chunks.")
    return splits

async def initialize_vector_store():
    """
    Inisialisasi atau muat ulang vector store dari data terbaru dari API.
    Ini akan mengisi variabel global _vector_store dan _retriever.
    """
    global _vector_store, _retriever

    logger.info("Initializing vector store...")
    embeddings = get_embeddings_model()

    # Ambil data terbaru dari API
    raw_documents = await _fetch_all_data_from_apis()

    # Split dokumen
    splits = _split_documents(raw_documents) if raw_documents else []

    # Inisialisasi ChromaDB
    # Jika direktori persistensi sudah ada dan berisi koleksi, muat ulang
    # Jika tidak, atau jika koleksi kosong, buat baru dari data API
    try:
        existing_store = Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
        if existing_store._collection.count() > 0:
            logger.info(f"Loaded existing vector store with {existing_store._collection.count()} documents.")
            # Jika Anda ingin memperbarui data, Anda perlu menghapus koleksi dan membuatnya kembali di sini
            # Atau menggabungkan logikanya. Untuk sekarang, kita gunakan yang sudah ada jika tidak kosong.
            # Kita asumsikan bahwa jika ada data, mungkin data tersebut valid atau perlu diperbarui secara eksplisit.
            # Untuk inisialisasi awal, kita selalu ingin mengisi dari API.
            # Kita hapus koleksi lama jika ingin menggantinya sepenuhnya.
            # Kita gunakan logika di bawah untuk membangun ulang.
            existing_count = existing_store._collection.count()
            logger.info(f"Found existing vector store with {existing_count} documents. Rebuilding from API data.")
            # Hapus koleksi lama
            existing_store.delete_collection()
            logger.info("Deleted old collection.")
        else:
            logger.info("Found existing vector store but it's empty. Rebuilding from API data.")
            # Koleksi ada tetapi kosong, hapus dan buat baru
            existing_store.delete_collection()
    except Exception as e:
        logger.info(f"Could not load existing vector store: {e}. Creating a new one from API data...")

    # Buat vector store baru dari data API yang telah dipecah
    if splits:
        _vector_store = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            collection_name=settings.CHROMA_COLLECTION_NAME,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
        logger.info("New vector store created and saved successfully.")
    else:
        # Jika tidak ada data dari API, buat vector store kosong
        _vector_store = Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
        logger.info("Created an empty vector store as no data was fetched from APIs.")

    # Buat retriever dari vector store yang baru dibuat/dimuat
    _retriever = _vector_store.as_retriever(search_kwargs={"k": 3})
    logger.info("Vector store and retriever initialized.")

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
    await initialize_vector_store()
    # initialize_vector_store sudah memperbarui _vector_store dan _retriever secara global
    logger.info("Vector store data refreshed.")