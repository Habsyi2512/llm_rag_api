from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.core.config import settings

def get_embeddings_model():
    print("Initializing embeddings model...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL_NAME,
        google_api_key=settings.GOOGLE_API_KEY
    )
    print("Embeddings model initialized.")
    return embeddings