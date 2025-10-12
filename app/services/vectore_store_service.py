from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
from app.services.api_client import fetch_faqs_from_api, fetch_documents_from_api
from app.services.embedding_service import get_embeddings_model
import asyncio

async def initialize_vector_store():
    print("Initializing vector store...")
    embeddings = get_embeddings_model()

    try:
        # Coba muat vector store yang sudah ada
        vector_store = Chroma(
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
        if vector_store._collection.count() == 0:
            raise FileNotFoundError("Vector store is empty.")
        print(f"Loaded existing vector store with {vector_store._collection.count()} documents.")
        return vector_store
    except Exception as e:
        print(f"Failed to load vector store: {e}. Creating a new one from API data...")

        # Ambil data dari API Laravel
        faq_docs_raw = await fetch_faqs_from_api()
        doc_docs_raw = await fetch_documents_from_api()

        all_docs_raw = faq_docs_raw + doc_docs_raw
        if not all_docs_raw:
            print("Warning: No data fetched from APIs. Creating an empty vector store.")
            # Mungkin perlu penanganan error jika tidak ada data
            return Chroma(
                collection_name=settings.CHROMA_COLLECTION_NAME,
                embedding_function=embeddings,
                persist_directory=settings.CHROMA_PERSIST_DIR,
            )

        # Konversi ke format Document LangChain
        documents = [Document(page_content=d['page_content'], metadata=d['metadata']) for d in all_docs_raw]

        # Split dokumen
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=300)
        splits = text_splitter.split_documents(documents)

        # Buat vector store baru
        vector_store = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            collection_name=settings.CHROMA_COLLECTION_NAME,
            persist_directory=settings.CHROMA_PERSIST_DIR,
        )
        print("Vector store successfully created and saved.")
        return vector_store

def get_retriever(vector_store):
    return vector_store.as_retriever(search_kwargs={"k": 3})