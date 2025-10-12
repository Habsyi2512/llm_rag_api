from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from app.core.config import settings
from app.models.state import State
from app.services.embedding_service import get_embeddings_model
from app.services.vector_store_service import get_retriever
from app.utils.prompt_templates import general_rag_prompt, tracking_prompt, intent_classification_prompt
from app.agents.document_tracking_agent import DocumentTrackingAgent
from app.utils.helpers import get_time, preprocess_question, extract_tracking_number
from app.core.redis_client import redis_client
import json

# Inisialisasi LLM dan komponen lainnya
print("Initializing LLM model...")
model = init_chat_model(
    model=settings.LLM_MODEL_NAME,
    model_provider="google_genai",
    google_api_key=settings.GOOGLE_API_KEY
)
print("LLM model initialized.")
embeddings = get_embeddings_model()

# Inisialisasi Vector Store dan Retriever (asumsi sudah diinisialisasi di awal)
# vector_store = initialize_vector_store() # Ini harus dijalankan terlebih dahulu
# retriever = get_retriever(vector_store)

# Inisialisasi Agent Pelacakan
tracking_agent = DocumentTrackingAgent()

# --- Nodes ---
async def classify_intent(state: State):
    print(f"Classifying intent for question: {state['question']}")
    chain = intent_classification_prompt | model
    response = await chain.ainvoke({"question": state["question"]})
    intent = response.content.strip().lower()
    if intent not in ['tracking', 'general']:
        intent = 'general' # Fallback
    print(f"Intent classified as: {intent}")
    return {"intent": intent}

async def handle_tracking_intent(state: State):
    print(f"Handling tracking intent for question: {state['question']}")
    # Cek apakah nomor registrasi ada di percakapan sebelumnya
    last_tracking_number = state.get('tracking_number')
    # Coba ekstrak dari pertanyaan saat ini
    current_tracking_number = extract_tracking_number(state['question'])

    # Jika tidak ada di state sebelumnya dan tidak ditemukan di pertanyaan saat ini
    if not last_tracking_number and not current_tracking_number:
        # Agent akan meminta nomor
        result = await tracking_agent.process_tracking_request(state['question'])
        if result['requires_number']:
            # Simpan bahwa intent adalah tracking, tapi belum ada nomor
            return {"answer": result['message'], "intent": "tracking_pending_number", "tracking_data": result['tracking_data']}
    else:
        # Gunakan nomor yang ditemukan
        number_to_use = current_tracking_number or last_tracking_number
        result = await tracking_agent.process_tracking_request(state['question'], number_to_use)
        # Perbarui nomor di state jika ditemukan di pertanyaan saat ini
        updated_state = {"tracking_data": result['tracking_data']}
        if current_tracking_number:
             updated_state['tracking_number'] = current_tracking_number
        if not result['requires_number']:
            # Jika berhasil mendapatkan data, kirimkan ke LLM untuk diformat
            current_date = get_time()
            chain = tracking_prompt | model
            formatted_response = await chain.ainvoke({
                "question": state["question"],
                "tracking_data": json.dumps(result['tracking_data'], indent=2, ensure_ascii=False),
                "date": current_date
            })
            updated_state['answer'] = formatted_response.content
        else:
            # Jika masih meminta nomor (mungkin nomor salah)
            updated_state['answer'] = result['message']
        return updated_state


async def retrieve_context(state: State):
    print(f"Retrieving context for question: {state['question']}")
    # Perlu mengakses retriever yang diinisialisasi di luar
    # Ini adalah contoh cara menggunakannya, pastikan retriever diinisialisasi
    # Misalnya, simpan retriever di instance class atau sebagai global var
    # global retriever # Jika disimpan sebagai global
    # retrieved_docs = retriever.get_relevant_documents(state["question"])
    # Kita asumsikan retriever diakses melalui service
    # Dalam implementasi nyata, inisialisasi retriever di awal dan simpan di tempat yang bisa diakses
    # Misalnya, simpan di instance class chain ini atau di global
    # Untuk saat ini, kita gunakan placeholder
    retrieved_docs = [] # Ganti dengan panggilan ke retriever sebenarnya
    print(f"Retrieved {len(retrieved_docs)} documents.")
    return {"context": retrieved_docs}

async def generate_general_answer(state: State):
    print("Generating general answer...")
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    current_date = get_time()

    chain = general_rag_prompt | model
    response = await chain.ainvoke({
        "question": state["question"],
        "context": docs_content,
        "date": current_date
    })
    print("General answer generated.")
    return {"answer": response.content}

# --- LangGraph Setup ---
def create_conversation_graph(retriever):
    def retrieve_context_with_retriever(state: State):
        print(f"Retrieving context for question: {state['question']}")
        retrieved_docs = retriever.get_relevant_documents(preprocess_question(state["question"]))
        print(f"Retrieved {len(retrieved_docs)} documents.")
        return {"context": retrieved_docs}

    def generate_general_answer_with_retriever(state: State):
        print("Generating general answer...")
        docs_content = "\n\n".join(doc.page_content for doc in state["context"])
        current_date = get_time()

        chain = general_rag_prompt | model
        response = chain.invoke({
            "question": state["question"],
            "context": docs_content,
            "date": current_date
        })
        print("General answer generated.")
        return {"answer": response.content}


    graph_builder = StateGraph(State)

    graph_builder.add_node("classifier", classify_intent)
    graph_builder.add_node("tracking_handler", handle_tracking_intent)
    graph_builder.add_node("retriever", retrieve_context_with_retriever) # Gunakan versi yang menerima retriever
    graph_builder.add_node("llm_generator", generate_general_answer_with_retriever) # Gunakan versi yang menerima retriever

    graph_builder.add_edge(START, "classifier")

    # Kondisional edge dari classifier
    def route_intent(state):
        intent = state.get("intent", "general")
        if intent == "tracking":
            return "tracking_handler"
        else:
            return "retriever" # Untuk intent general

    graph_builder.add_conditional_edges(
        "classifier",
        route_intent,
        {
            "tracking": "tracking_handler",
            "general": "retriever"
        }
    )
    graph_builder.add_edge("tracking_handler", END)
    graph_builder.add_edge("retriever", "llm_generator")
    graph_builder.add_edge("llm_generator", END)

    graph = graph_builder.compile()
    print("LangGraph compiled.")
    return graph