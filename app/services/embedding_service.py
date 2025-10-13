# from langchain_google_genai import GoogleGenerativeAIEmbeddings

from langchain_ollama import OllamaEmbeddings
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# def get_embeddings_model():
#     print("Initializing embeddings model...")
    # embeddings = GoogleGenerativeAIEmbeddings(
    #     model=settings.EMBEDDING_MODEL_NAME,
    #     google_api_key=settings.GOOGLE_API_KEY
    # )
    # print("Embeddings model initialized.")
    # return embeddings

def get_embeddings_model():
    print("Initializing Ollama embeddings model...")
    logger.info("Initializing Ollama embeddings model...")

    # Gunakan model embedding dari Ollama
    # Pastikan model ini sudah di-pull di Ollama
    embeddings = OllamaEmbeddings(
        model=settings.EMBEDDING_MODEL_NAME, # Contoh: "nomic-embed-text"
        base_url=settings.OLLAMA_BASE_URL # Contoh: "http://localhost:11434"
    )
    print("Ollama embeddings model initialized.")
    logger.info("Ollama embeddings model initialized.")
    return embeddings