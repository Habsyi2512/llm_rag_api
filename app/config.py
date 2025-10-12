import os
from dotenv import load_dotenv

load_dotenv()

# variables untuk konfigurasi bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_SECRET_TOKEN = os.getenv("TELEGRAM_SECRET_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_PROVIDER = os.getenv("GOOGLE_PROVIDER", "google_genai")  
GOOGLE_SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")

# LLM Configuration (pakai Ollama model lokal)

# PDF Configuration
PDF_PATH = "app/data/data-publik-disdukcapil.pdf"
CHROMA_PERSIST_DIR = "./chroma_langchain_db"
CHROMA_COLLECTION_NAME = "chatbot_lokal"

# Validation
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set.")
if not TELEGRAM_SECRET_TOKEN:
    raise ValueError("TELEGRAM_SECRET_TOKEN environment variable is not set.")