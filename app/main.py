from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from app.core.config import settings
from app.services.vector_store_service import initialize_vector_store, get_retriever
from app.chains.conversation_chain import create_conversation_graph
from app.schemas.requests import ChatRequest, ChatResponse
from app.models.state import State
import asyncio

# Variabel global untuk menyimpan komponen yang diinisialisasi
vector_store = None
retriever = None
graph = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_store, retriever, graph
    print("Starting up LLM RAG Service...")
    # Inisialisasi Vector Store
    vector_store = await initialize_vector_store()
    # Inisialisasi Retriever
    retriever = get_retriever()
    # Inisialisasi LangGraph
    graph = create_conversation_graph(retriever)
    print("LLM RAG Service is ready!")
    yield
    print("Shutting down LLM RAG Service...")

app = FastAPI(
    title="Chatbot Layanan Informasi Publik Disdukcapil Kabupaten Kepulauan Anambas",
    lifespan=lifespan
)

@app.post("/chat", response_model=ChatResponse)
async def chatbot_endpoint(request: ChatRequest):
    global graph
    if not graph:
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
        final_state = await graph.ainvoke(initial_state)
        response_message = final_state.get("answer", "Maaf, saya tidak dapat memproses permintaan Anda saat ini.")
        intent = final_state.get("intent", "general")
        tracking_data = final_state.get("tracking_data", None)

        return ChatResponse(
            response=response_message,
            intent=intent,
            tracking_data=tracking_data
        )
    except Exception as e:
        print(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during processing.")

@app.get("/health")
async def health_check():
    return {"status": "ok", "llm_ready": bool(graph)}

# --- Endpoint untuk refresh data ke vector store ---
@app.post("/refresh-data")
async def refresh_data():
    global vector_store, retriever, graph
    try:
        # Ambil ulang data dari API
        from app.services.api_client import fetch_faqs_from_api, fetch_documents_from_api
        faq_docs_raw = await fetch_faqs_from_api()
        doc_docs_raw = await fetch_documents_from_api()
        all_docs_raw = faq_docs_raw + doc_docs_raw

        if not all_docs_raw:
            return {"message": "No new data fetched from APIs."}

        from langchain_core.documents import Document
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        documents = [Document(page_content=d['page_content'], metadata=d['metadata']) for d in all_docs_raw]

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=300)
        splits = text_splitter.split_documents(documents)

        # Dapatkan nama koleksi dari config
        collection_name = settings.CHROMA_COLLECTION_NAME

        # Hapus koleksi lama
        vector_store.delete_collection(collection_name=collection_name)
        print(f"Deleted old collection: {collection_name}")

        # Buat koleksi baru
        new_vector_store = await initialize_vector_store() # Fungsi ini sekarang membuat koleksi baru jika tidak ada
        # Atau gunakan Chroma.from_documents secara langsung untuk koleksi tertentu
        # new_vector_store = Chroma.from_documents(
        #     documents=splits,
        #     embedding=embeddings_model, # Anda perlu mengakses embeddings_model
        #     collection_name=collection_name,
        #     persist_directory=settings.CHROMA_PERSIST_DIR,
        # )
        # vector_store = new_vector_store

        # Perbarui retriever dan graph
        retriever = get_retriever(new_vector_store)
        graph = create_conversation_graph(retriever) # Recreate graph dengan retriever baru
        vector_store = new_vector_store # Update global var

        return {"message": "Data refreshed successfully."}
    except Exception as e:
        print(f"Error refreshing  {e}")
        raise HTTPException(status_code=500, detail=f"Error refreshing data: {e}")
