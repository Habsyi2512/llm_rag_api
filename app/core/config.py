import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import ConfigDict # Impor ConfigDict

load_dotenv()

class Settings(BaseSettings):
    # Google
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_LLM_MODEL_NAME: str = os.getenv("GOOGLE_LLM_MODEL_NAME", "gemini-2.5-flash")
    GOOGLE_EMBEDDING_MODEL_NAME: str = os.getenv("GOOGLE_EMBEDDING_MODEL_NAME", "")

    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_LLM_MODEL_NAME: str = os.getenv("OLLAMA_LLM_MODEL_NAME", "nomic-llama-2-7b")
    OLLAMA_EMBEDDING_MODEL_NAME: str = os.getenv("OLLAMA_EMBEDDING_MODEL_NAME", "")

    # Laravel API
    LARAVEL_API_BASE_URL: str = os.getenv("LARAVEL_API_BASE_URL", "http://localhost:8000")
    LARAVEL_API_TIMEOUT: int = int(os.getenv("LARAVEL_API_TIMEOUT", "30"))
    LARAVEL_API_TOKEN: str = os.getenv("LARAVEL_API_TOKEN", "token")

    # ChromaDB
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./vector_store_db_llm_rag")
    CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "faq_document_vector")

    # AI Provider
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google_genai")
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "ollama")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")


    # Menambahkan model_config untuk konfigurasi Pydantic V2
    model_config = ConfigDict(
        env_file=".env",        # Lokasi file .env
        extra="ignore"
    )

# Inisialisasi instance settings
settings = Settings()

# print settings