# app/chains/conversation_chain.py

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from app.core.config import settings
from app.models.state import State
from app.utils.prompt_templates import general_rag_prompt, tracking_prompt, intent_classification_prompt
from app.agents.document_tracking_agent import DocumentTrackingAgent
from app.utils.helpers import get_time, preprocess_question
from app.core.redis_client import redis_client
import json
import logging

logger = logging.getLogger(__name__)

# Inisialisasi LLM dan agent di tingkat modul/file (ini bisa dilakukan di sini)
logger.info("Initializing LLM model in chain...")
model = init_chat_model(
    model=settings.LLM_MODEL_NAME,
    model_provider="google_genai",
    google_api_key=settings.GOOGLE_API_KEY
)
logger.info("LLM model initialized in chain.")
tracking_agent = DocumentTrackingAgent()

# --- Nodes ---
# ... (definisi fungsi-fungsi node seperti sebelumnya, tapi tanpa mengakses retriever global di sini) ...

# Node untuk mengambil konteks dari retriever
def retrieve_context_node(retriever): # Fungsi pembungkus untuk LangGraph yang menerima retriever
    async def node_func(state: State):
        print(f"Retrieving context for question: {state['question']}")
        # Preprocess question sebelum mengirim ke retriever
        cleaned_question = preprocess_question(state["question"])
        # Panggil metode retriever
        retrieved_docs = retriever.get_relevant_documents(cleaned_question)
        print(f"Retrieved {len(retrieved_docs)} documents.")
        return {"context": retrieved_docs}
    return node_func

# Node untuk menghasilkan jawaban umum berdasarkan konteks
def generate_general_answer(state: State): # Tidak perlu menerima retriever
    print("Generating general answer...")
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    current_date = get_time()

    chain = general_rag_prompt | model
    response = chain.invoke({ # Gunakan .invoke() untuk sync
        "question": state["question"],
        "context": docs_content,
        "date": current_date
    })
    print("General answer generated.")
    return {"answer": response.content}

# Node untuk klasifikasi intent
async def classify_intent(state: State):
    print(f"Classifying intent for question: {state['question']}")
    chain = intent_classification_prompt | model
    response = await chain.ainvoke({"question": state["question"]}) # Gunakan .ainvoke() untuk async
    intent = response.content.strip().lower()
    if intent not in ['tracking', 'general']:
        intent = 'general' # Fallback
    print(f"Intent classified as: {intent}")
    return {"intent": intent}

# Node untuk menangani intent pelacakan
# async def handle_tracking_intent(state: State):
#     print(f"Handling tracking intent for question: {state['question']}")
#     from app.utils.helpers import extract_tracking_number # Impor di sini untuk menghindari circular import jika perlu
#     # Cek apakah nomor registrasi ada di percakapan sebelumnya
#     last_tracking_number = state.get('tracking_number')
#     # Coba ekstrak dari pertanyaan saat ini
#     current_tracking_number = extract_tracking_number(state['question'])

#     # Jika tidak ada di state sebelumnya dan tidak ditemukan di pertanyaan saat ini
#     if not last_tracking_number and not current_tracking_number:
#         # Agent akan meminta nomor
#         result = await tracking_agent.process_tracking_request(state['question'])
#         if result['requires_number']:
#             # Simpan bahwa intent adalah tracking, tapi belum ada nomor
#             return {"answer": result['message'], "intent": "tracking_pending_number", "tracking_data": result['tracking_data']}
#     else:
#         # Gunakan nomor yang ditemukan
#         number_to_use = current_tracking_number or last_tracking_number
#         result = await tracking_agent.process_tracking_request(state['question'], number_to_use)
#         # Perbarui nomor di state jika ditemukan di pertanyaan saat ini
#         updated_state = {"tracking_data": result['tracking_data']}
#         if current_tracking_number:
#              updated_state['tracking_number'] = current_tracking_number
#         if not result['requires_number']:
#             # Jika berhasil mendapatkan data, kirimkan ke LLM untuk diformat
#             current_date = get_time()
#             chain = tracking_prompt | model
#             formatted_response = await chain.ainvoke({
#                 "question": state["question"],
#                 "tracking_data": json.dumps(result['tracking_data'], indent=2, ensure_ascii=False),
#                 "date": current_date
#             })
#             updated_state['answer'] = formatted_response.content
#         else:
#             # Jika masih meminta nomor (mungkin nomor salah)
#             updated_state['answer'] = result['message']
#         return updated_state
#     # Fallback jika semua percobaan gagal
#     return {"answer": "Maaf, saya tidak bisa memproses permintaan pelacakan dokumen saat ini."}

# Node untuk menangani intent pelacakan
async def handle_tracking_intent(state: State):
    print(f"Handling tracking intent for question: {state['question']}")
    # Impor di sini untuk menghindari circular import jika perlu
    from app.utils.helpers import extract_tracking_number

    # Cek apakah nomor registrasi ada di percakapan sebelumnya
    last_tracking_number = state.get('tracking_number')
    print(f"  Last known tracking number from state: '{last_tracking_number}'") # Log nilai sebelumnya
    # Coba ekstrak dari pertanyaan saat ini
    current_tracking_question = state['question']
    current_tracking_number = extract_tracking_number(current_tracking_question)
    print(f"  Extracted number from current question ('{current_tracking_question}'): '{current_tracking_number}'") # Log nilai yang diekstrak

    # Jika tidak ada di state sebelumnya dan tidak ditemukan di pertanyaan saat ini
    if not last_tracking_number and not current_tracking_number:
        print("  -> No number found, requesting number.")
        # Agent akan meminta nomor
        try:
            result = await tracking_agent.process_tracking_request(state['question'])
            if result.get('requires_number'):
                # Simpan bahwa intent adalah tracking, tapi belum ada nomor
                return {"answer": result.get('message', "Mohon berikan nomor registrasi."), "intent": "tracking_pending_number", "tracking_data": result.get('tracking_data')}
            else:
                # Jika agent mengembalikan jawaban tanpa meminta nomor, mungkin karena error parsing
                return {"answer": result.get('message', "Terjadi kesalahan saat memproses permintaan pelacakan."), "intent": "tracking_error", "tracking_data": result.get('tracking_data')}
        except Exception as e:
            logger.error(f"Error in tracking_agent.process_tracking_request: {e}")
            return {"answer": "Terjadi kesalahan internal saat memproses permintaan pelacakan.", "intent": "tracking_error", "tracking_data": None}
    else:
        print(f"  -> Number found (last: '{last_tracking_number}', current: '{current_tracking_number}'), attempting to fetch status.")
        # Gunakan nomor yang ditemukan
        number_to_use = current_tracking_number or last_tracking_number
        print(f"  -> Using number: '{number_to_use}' for API call.")
        try:
            result = await tracking_agent.process_tracking_request(state['question'], number_to_use)
            # Perbarui nomor di state jika ditemukan di pertanyaan saat ini
            updated_state = {"tracking_data": result.get('tracking_data')}
            if current_tracking_number:
                 updated_state['tracking_number'] = current_tracking_number
            if not result.get('requires_number'):
                # Jika berhasil mendapatkan data, kirimkan ke LLM untuk diformat
                current_date = get_time()
                chain = tracking_prompt | model
                formatted_response = await chain.ainvoke({
                    "question": state["question"],
                    "tracking_data": json.dumps(result.get('tracking_data', {}), indent=2, ensure_ascii=False),
                    "date": current_date
                })
                updated_state['answer'] = formatted_response.content
            else:
                # Jika masih meminta nomor (mungkin nomor salah dari agent)
                updated_state['answer'] = result.get('message', "Mohon berikan nomor registrasi yang valid.")
            return updated_state
        except Exception as e:
            logger.error(f"Error in tracking_agent.process_tracking_request with number {number_to_use}: {e}")
            # Kembalikan pesan error, tetapi tetap simpan nomor jika ditemukan
            error_state = {"tracking_data": None}
            if current_tracking_number:
                 error_state['tracking_number'] = current_tracking_number
            error_state['answer'] = "Terjadi kesalahan saat menghubungi sistem pelacakan. Silakan coba lagi nanti."
            error_state['intent'] = "tracking_error"
            return error_state


# --- LangGraph Setup ---
def create_conversation_graph(retriever): # Terima retriever sebagai parameter
    graph_builder = StateGraph(State)

    # Tambahkan node-node ke graph
    graph_builder.add_node("classifier", classify_intent)
    graph_builder.add_node("tracking_handler", handle_tracking_intent)
    # Gunakan fungsi pembungkus yang membawa retriever
    graph_builder.add_node("retriever", retrieve_context_node(retriever)) # <-- Di sini, fungsi pembungkus menerima retriever
    graph_builder.add_node("llm_generator", generate_general_answer)

    # Tambahkan edge awal
    graph_builder.add_edge(START, "classifier")

    # Kondisional edge dari classifier
    def route_intent(state):
        intent = state.get("intent", "general")
        if intent in ["tracking", "tracking_pending_number"]: # Tangani juga status pending number
            return "tracking_handler"
        else:
            return "retriever" # Untuk intent general

    graph_builder.add_conditional_edges(
        "classifier",
        route_intent,
        {
            "tracking_handler": "tracking_handler",
            "tracking_pending_number": "tracking_handler", # Arahkan ke handler juga jika meminta nomor
            "retriever": "retriever"
        }
    )
    graph_builder.add_edge("tracking_handler", END)
    graph_builder.add_edge("retriever", "llm_generator")
    graph_builder.add_edge("llm_generator", END)

    graph = graph_builder.compile()
    logger.info("LangGraph compiled.")
    print("LangGraph compiled.")
    return graph