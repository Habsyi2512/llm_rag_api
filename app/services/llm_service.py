# app/services/llm_service.py

import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_llm_model():
    provider = settings.LLM_PROVIDER.lower()

    if provider == "google":
        print("Initializing Google LLM model...")
        print("GOOGLE_LLM_MODEL_NAME:", settings.GOOGLE_LLM_MODEL_NAME)
        print("GOOGLE_API_KEY:", settings.GOOGLE_API_KEY)
        logger.info("Initializing Google LLM model...")
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is required when LLM_PROVIDER is 'google'.")
        llm = ChatGoogleGenerativeAI(
            model=settings.GOOGLE_LLM_MODEL_NAME,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1,
        )
        logger.info("Google LLM model initialized.")
    elif provider == "ollama":
        print("Initializing Ollama LLM model...")
        print("OLLAMA_LLM_MODEL_NAME:", settings.OLLAMA_LLM_MODEL_NAME)
        logger.info("Initializing Ollama LLM model...")
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            model=settings.OLLAMA_LLM_MODEL_NAME,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.1,
        )
        logger.info("Ollama LLM model initialized.")
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}. Supported values are 'google' and 'ollama'.")
    
    # --- Debugging: Mulai ---
    print("LLM Model:")
    answer = llm.invoke('halo')
    print(f"Answer: {answer.content}")
    # --- Debugging: Selesai ---
    return llm