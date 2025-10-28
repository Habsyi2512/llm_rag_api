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
    """Mengambil semua data dari API Laravel dan mengonversinya ke dokumen LangChain dengan metadata bersih."""
    logger.info("Fetching data from Laravel APIs...")
    
    faq_docs_raw = await fetch_faqs_from_api()
    doc_docs_raw = await fetch_documents_from_api()
    all_docs_raw = []

    # ===== FAQ =====
    for d in faq_docs_raw:
        metadata = d.get('metadata', {})
        if 'id' in d:
            metadata['faq_id'] = str(d['id'])
        metadata['type'] = 'faq'
        metadata['source'] = metadata.get('source', 'faq')
        # Tambahkan created_at / updated_at jika tersedia
        if 'created_at' in d:
            metadata['created_at'] = d['created_at']
        if 'updated_at' in d:
            metadata['updated_at'] = d['updated_at']
        d['metadata'] = metadata
        all_docs_raw.append(d)

    # ===== Documents =====
    for d in doc_docs_raw:
        metadata = d.get('metadata', {})
        if 'id' in d:
            metadata['doc_id'] = str(d['id'])
        metadata['type'] = 'document'
        metadata['source'] = metadata.get('source', 'document')
        if 'created_at' in d:
            metadata['created_at'] = d['created_at']
        if 'updated_at' in d:
            metadata['updated_at'] = d['updated_at']
        d['metadata'] = metadata
        all_docs_raw.append(d)

    if not all_docs_raw:
        logger.warning("No data fetched from APIs. Vector store might be empty.")
        return []

    # ===== Konversi ke Document LangChain =====
    documents = [
        Document(page_content=d['page_content'], metadata=d['metadata'])
        for d in all_docs_raw
    ]

    logger.info(f"Successfully fetched {len(documents)} documents from APIs with metadata.")
    return documents


def _split_documents(documents: List[Document]) -> List[Document]:
    """Memecah dokumen menjadi potongan-potongan (chunks) yang lebih kecil, sambil menjaga metadata."""
    logger.info("Splitting documents...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
    )

    from app.utils.helpers import preprocess_question  # Impor lokal untuk menghindari circular import

    processed_docs = []
    for doc in documents:
        processed_content = preprocess_question(doc.page_content)
        processed_docs.append(Document(page_content=processed_content, metadata=doc.metadata))

    splits = text_splitter.split_documents(processed_docs)

    # Tambahkan chunk_index di metadata agar bisa trace kembali ke dokumen asli
    chunked_docs = []
    for original_doc in processed_docs:
        original_chunks = text_splitter.split_text(original_doc.page_content)
        for i, chunk in enumerate(original_chunks):
            metadata = original_doc.metadata.copy()
            metadata['chunk_index'] = i
            chunked_docs.append(Document(page_content=chunk, metadata=metadata))

    logger.info(f"Documents split into {len(chunked_docs)} chunks.")
    return chunked_docs




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
                _retriever = _vector_store.as_retriever(search_kwargs={"k": 3}, )
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
    
    _retriever = _vector_store.as_retriever(search_kwargs={"k": 3}, )
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

async def add_faq_to_vector_store(content: str, metadata: dict):
    """
    Menambahkan satu FAQ baru ke vector store dengan metadata yang sudah dinormalisasi.

    metadata yang diterima bisa berisi:
    - faq_id (dari Laravel)
    - created_at / updated_at
    - source
    """
    print(f"cek metadata sebelum ditambahkan ke vector store: {metadata}")
    global _vector_store
    if _vector_store is None:
        raise RuntimeError("Vector store not initialized")

    from langchain_core.documents import Document

    # Salin metadata agar tidak mengubah dict asli
    metadata = metadata.copy() if metadata else {}

    if 'faq_id' not in metadata:
        raise ValueError("faq_id harus ada di metadata")
    else:
        metadata['faq_id'] = str(metadata['faq_id'])  # Pastikan faq_id adalah string

    # Pastikan type dan source sesuai standar
    metadata['type'] = 'faq'
    metadata['source'] = metadata.get('source', 'faq')

    # Tambahkan created_at / updated_at jika ada
    if 'created_at' in metadata:
        metadata['created_at'] = metadata['created_at']
    if 'updated_at' in metadata:
        metadata['updated_at'] = metadata['updated_at']

    # Buat Document LangChain dan tambahkan ke vector store
    doc = Document(page_content=content, metadata=metadata)
    _vector_store.add_documents([doc])

    return {
        "status": "success",
        "message": f"FAQ {metadata['faq_id']} added to vector store"
    }


async def update_faq_in_vector_store(faq_id: str, new_content: str, new_metadata: dict = None):
    """
    Update FAQ di vector store berdasarkan faq_id.
    - new_content: teks pertanyaan + jawaban baru
    - new_metadata: dict opsional untuk menambahkan/mengubah metadata
    """
    global _vector_store
    if _vector_store is None:
        raise RuntimeError("Vector store not initialized. Call initialize_vector_store first.")

    # Hapus dulu dokumen lama
    _vector_store.delete(where={"faq_id": faq_id})

    # Siapkan metadata baru
    metadata = new_metadata.copy() if new_metadata else {}
    metadata['faq_id'] = faq_id
    metadata['type'] = 'faq'
    metadata['source'] = metadata.get('source', 'faq')

    # Masukkan kembali sebagai dokumen baru
    doc = Document(page_content=new_content, metadata=metadata)
    embeddings = get_embeddings_model()
    _vector_store.add_documents([doc], embedding=embeddings)

    return {"status": "success", "message": f"FAQ {faq_id} updated in vector store."}


async def delete_faq_from_vector_store(faq_id: str):
    """
    Delete FAQ di vector store berdasarkan faq_id.
    """
    global _vector_store
    if _vector_store is None:
        raise RuntimeError("Vector store not initialized. Call initialize_vector_store first.")
    
    # melakukan pengecekan terhadap faq_id sebelum penghapusan
    cek_faq = _vector_store.get(where={"faq_id": faq_id})  # Akan melempar error jika tidak ditemukan
    if not cek_faq['documents']:
        logger.warning(f"FAQ {faq_id} not found in vector store.")
        return {"status": "failed", "message": f"FAQ {faq_id} not found in vector store."}
    
    # Hapus dokumen
    logger.info(f"Deleting FAQ {faq_id} from vector store...")
    _vector_store.delete(where={"faq_id": faq_id})
    return {"status": "success", "message": f"FAQ {faq_id} deleted from vector store."}
