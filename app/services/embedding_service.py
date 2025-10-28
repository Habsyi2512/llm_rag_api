from langchain_ollama import OllamaEmbeddings
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_embeddings_model():
    print("Initializing Ollama embeddings model uy...")
    logger.info("Initializing Ollama embeddings model...")

    # Gunakan model embedding dari Ollama
    # Pastikan model ini sudah di-pull di Ollama
    embeddings = OllamaEmbeddings(
        model=settings.OLLAMA_EMBEDDING_MODEL_NAME, # Contoh: "nomic-embed-text"
        base_url=settings.OLLAMA_BASE_URL # Contoh: "http://localhost:11434"
    )
    logger.info("Ollama embeddings model initialized.")
    print("embedding model berjalan ✅")
    return embeddings