import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import ConfigDict # Impor ConfigDict

load_dotenv()

class Settings(BaseSettings):
    # Google
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gemini-2.0-flash")
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "models/embedding-001")

    # Laravel API
    LARAVEL_API_BASE_URL: str = os.getenv("LARAVEL_API_BASE_URL", "http://localhost:8000/api")
    LARAVEL_API_TIMEOUT: int = int(os.getenv("LARAVEL_API_TIMEOUT", "30"))

    # ChromaDB
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./vector_store_db_llm_rag")
    CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "faq_document_vector")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")


    # Menambahkan model_config untuk konfigurasi Pydantic V2
    model_config = ConfigDict(
        env_file=".env",        # Lokasi file .env
        extra="ignore"
    )

# Inisialisasi instance settings
settings = Settings()
