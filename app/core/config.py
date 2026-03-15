import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import ConfigDict # Impor ConfigDict

load_dotenv()

class Settings(BaseSettings):
    FASTAPI_API_KEY: str = os.getenv("FASTAPI_API_KEY", "")

    # Google
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_LLM_MODEL_NAME: str = os.getenv("GOOGLE_LLM_MODEL_NAME", "gemini-2.5-flash")
    GOOGLE_EMBEDDING_MODEL_NAME: str = os.getenv("GOOGLE_EMBEDDING_MODEL_NAME", "")

    # Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_LLM_MODEL_NAME: str = os.getenv("OLLAMA_LLM_MODEL_NAME", "")
    OLLAMA_EMBEDDING_MODEL_NAME: str = os.getenv("OLLAMA_EMBEDDING_MODEL_NAME", "bge-m3:latest")

    # Laravel API
    LARAVEL_API_BASE_URL: str = os.getenv("LARAVEL_API_BASE_URL", "http://127.0.0.1:8002/api")
    LARAVEL_PUBLIC_URL: str = os.getenv("LARAVEL_PUBLIC_URL", "")
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

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "3306")
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "rag_db")
    
    # Default to MySQL if host is provided, otherwise fallback to SQLite
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}" 
        if os.getenv("DB_HOST") else "sqlite+aiosqlite:///./rag_database.db"
    )
    
    # JWT Settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "9dfd664c-b691-42e9-b6e0-d5f77c57d692")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_HOURS: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "2"))
    
    # Admin Credentials (Hardcoded for simple refactor, usually in DB)
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@anambas.go.id")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "passwordanambas")


    # Menambahkan model_config untuk konfigurasi Pydantic V2
    model_config = ConfigDict(
        env_file=".env",        # Lokasi file .env
        extra="ignore"
    )

# Inisialisasi instance settings
settings = Settings()

# print settings