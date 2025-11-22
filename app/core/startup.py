import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.services.vector_store.service import (
    initialize_vector_store,
    get_retriever
)
from app.chains.conversation_chain import create_conversation_graph
from app.core.config import settings

logger = logging.getLogger(__name__)

_graph = None  # state global internal

def get_graph():
    return _graph

def set_graph(new_graph):
    global _graph
    _graph = new_graph

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph
    logger.info("Starting up LLM RAG Service...")
    print("Starting up LLM RAG Service...")

    try:
        await initialize_vector_store(
            force_refresh=False, 
            persist_directory=settings.CHROMA_PERSIST_DIR, 
            collection_name=settings.CHROMA_COLLECTION_NAME,
            )
        retriever = get_retriever()
        _graph = create_conversation_graph(retriever)
        logger.info("LangGraph compiled and ready.")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    logger.info("Shutting down LLM RAG Service...")
    print("Shutting down LLM RAG Service...")

async def init_graph():
    """
    Inisialisasi manual graph LLM tanpa menjalankan FastAPI server.
    Berguna untuk testing BERTScore atau evaluasi offline.
    """
    global _graph
    if _graph is not None:
        return _graph  # sudah siap

    logger.info("Manual init_graph() called...")
    print("🚀 Inisialisasi manual graph LLM...")

    try:
        await initialize_vector_store(
            force_refresh=False,
            persist_directory=settings.CHROMA_PERSIST_DIR,
            collection_name=settings.CHROMA_COLLECTION_NAME,
        )
        retriever = get_retriever()
        _graph = create_conversation_graph(retriever)
        logger.info("LangGraph compiled and ready (manual init).")
        print("✅ Graph siap digunakan!")
    except Exception as e:
        logger.error(f"Manual init_graph() gagal: {e}")
        raise

    return _graph
