# app/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Security, Body
import logging
from app.auth import verify_api_key
from fastapi.middleware.cors import CORSMiddleware

# Impor fungsi-fungsi dari service
from app.services.vector_store_service import initialize_vector_store, get_retriever, refresh_vector_store_data
from app.chains.conversation_chain import create_conversation_graph
from app.schemas.requests import ChatRequest, ChatResponse
from app.models.state import State

from app.services.vector_store_service import (
    initialize_vector_store,
    get_retriever,
    refresh_vector_store_data,
    update_faq_in_vector_store,
    delete_faq_from_vector_store,
    add_faq_to_vector_store
)


logger = logging.getLogger(__name__)

# Variabel global hanya untuk komponen yang dibutuhkan oleh endpoint
_graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph # Kita perlu memperbarui variabel global graph
    print("Starting up LLM RAG Service...")
    logger.info("Starting up LLM RAG Service...")

    try:
        # 1. Inisialisasi Vector Store dan Retriever melalui service
        # Ini akan mengisi variabel global _vector_store dan _retriever di vector_store_service
        await initialize_vector_store(force_refresh=False) # Gunakan cache jika ada saat startup
        logger.info("Vector store initialized via service.")

        # 2. Ambil retriever yang telah dibuat oleh service
        # Fungsi get_retriever dari vector_store_service tidak menerima argumen.
        # Ia mengakses _retriever yang sudah diinisialisasi secara global oleh initialize_vector_store.
        retriever = get_retriever()
        logger.info("Retriever obtained from service.")

        # 3. Inisialisasi LangGraph dengan retriever yang benar
        _graph = create_conversation_graph(retriever) # Kirim retriever ke fungsi pembuatan graph
        logger.info("LangGraph compiled and ready.")
    except Exception as e:
        logger.error(f"Failed to initialize services during startup: {e}")
        print(f"Failed to initialize services during startup: {e}") # Juga log ke console
        raise # Melempar error agar aplikasi tidak berjalan jika inisialisasi gagal

    print("LLM RAG Service is ready!")
    logger.info("LLM RAG Service is ready!")
    yield
    print("Shutting down LLM RAG Service...")
    logger.info("Shutting down LLM RAG Service...")

app = FastAPI(
    title="Chatbot Layanan Informasi Publik Disdukcapil Kabupaten Kepulauan Anambas",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Semua origin diizinkan
    allow_credentials=True,
    allow_methods=["*"],  # Semua metode HTTP diizinkan (GET, POST, dsb)
    allow_headers=["*"],  # Semua header diizinkan
)

@app.post("/chat", response_model=ChatResponse)
async def chatbot_endpoint(request: ChatRequest, api_key: str = Security(verify_api_key)):
    global _graph
    if not _graph:
        logger.error("Graph is not ready!")
        raise HTTPException(status_code=503, detail="Service not ready, please try again later.")

    # State awal
    initial_state: State = {
        "question": request.message,
        "context": [],
        "answer": "",
        "conversation_history": [], # Implementasi riwayat percakapan bisa ditambahkan
        "user_id": request.user_id or "anonymous", # Gunakan ID pengguna atau sesi
        "intent": "unknown",
        "tracking_number": None,
        "tracking_data": None
    }

    try:
        # Jalankan graph
        final_state = await _graph.ainvoke(initial_state) # Gunakan _graph yang benar
        response_message = final_state.get("answer", "Maaf, saya tidak dapat memproses permintaan Anda saat ini.")
        intent = final_state.get("intent", "general")
        tracking_data = final_state.get("tracking_data", None)

        return ChatResponse(
            response=response_message,
            intent=intent,
            tracking_data=tracking_data
        )
    except Exception as e:
        logger.error(f"Error processing chat request: {e}")
        print(f"Error processing chat request: {e}") # Juga log ke console
        raise HTTPException(status_code=500, detail="Internal server error during processing.")

@app.get("/health")
async def health_check():
    return {"status": "ok", "llm_ready": bool(_graph)}

# --- Endpoint untuk refresh data ke vector store ---
@app.post("/refresh-data")
async def refresh_data():
    global _graph # Kita perlu memperbarui graph setelah refresh data
    try:
        # Panggil fungsi refresh dari service
        await refresh_vector_store_data()

        # Ambil retriever yang baru
        retriever = get_retriever() # Fungsi ini dari vector_store_service

        # Buat graph baru dengan retriever yang baru
        _graph = create_conversation_graph(retriever)
        logger.info("Graph recreated after data refresh.")

        return {"message": "Data and graph refreshed successfully."}
    except Exception as e:
        logger.error(f"Error refreshing  {e}")
        print(f"Error refreshing  {e}") # Juga log ke console
        raise HTTPException(status_code=500, detail=f"Error refreshing  {e}")
    
@app.post("/vector-store/faqs")
async def create_faq_endpoint(
    payload: dict = Body(...),
    api_key: str = Security(verify_api_key)
):
    """
    Tambahkan FAQ baru ke vector store
    Payload contoh:
    {
        "content": "Pertanyaan dan jawaban baru",
        "metadata": {"faq_id": "123", "created_at": "2025-10-27T00:00:00Z"}
    }
    """
    content = payload.get("content")
    metadata = payload.get("metadata", {})

    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    try:
        result = await add_faq_to_vector_store(content, metadata)
        return result
    except Exception as e:
        logger.error(f"Error creating FAQ: {e}")
        raise HTTPException(status_code=500, detail=f"Error creating FAQ: {e}")
    
@app.put("/vector-store/faqs/{faq_id}")
async def update_faq_endpoint(
    faq_id: str,
    payload: dict = Body(...),
    api_key: str = Security(verify_api_key)
):
    """
    Update FAQ di vector store berdasarkan faq_id
    Payload contoh:
    {
        "content": "Pertanyaan dan jawaban baru",
        "metadata": {"created_at": "2025-10-27T00:00:00Z"}
    }
    """
    content = payload.get("content")
    metadata = payload.get("metadata", None)

    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    try:
        result = await update_faq_in_vector_store(faq_id, content, metadata)
        return result
    except Exception as e:
        logger.error(f"Error updating FAQ {faq_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating FAQ {faq_id}: {e}")
    
@app.delete("/vector-store/faqs/{faq_id}")
async def delete_faq_endpoint(
    faq_id: str,
    api_key: str = Security(verify_api_key)
):
    """
    Delete FAQ di vector store berdasarkan faq_id
    """
    try:
        result = await delete_faq_from_vector_store(faq_id)
        return result
    except Exception as e:
        logger.error(f"Error deleting FAQ {faq_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting FAQ {faq_id}: {e}")
