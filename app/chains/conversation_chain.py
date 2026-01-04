from langgraph.graph import StateGraph, START, END
from app.core.config import settings
from app.models.state import State
from app.utils.prompt_templates import general_rag_prompt, tracking_prompt, intent_classification_prompt, contextualize_q_prompt
from app.agents.document_tracking_agent import DocumentTrackingAgent
from app.utils.helpers import get_time, preprocess_question
from app.services.llm_service import get_llm_model
import json
import logging
import re
from langchain_core.messages import HumanMessage, AIMessage

logger = logging.getLogger(__name__)

# Inisialisasi LLM dan agent di tingkat modul/file (ini bisa dilakukan di sini)
logger.info("Initializing LLM model in chain...")
model = get_llm_model()
logger.info("LLM model initialized in chain.")
tracking_agent = DocumentTrackingAgent()

# --- Nodes ---

# Node untuk memformulasikan ulang pertanyaan berdasarkan history
async def contextualize_question(state: State):
    print(f"Checking if question needs contextualization: {state['question']}")
    
    if not state.get("conversation_history"):
        print("No history, skipping contextualization.")
        return {}

    # Format history
    history_messages = []
    for msg in state["conversation_history"]:
        if msg.get("role") == "user":
            history_messages.append(HumanMessage(content=msg.get("content", "")))
        elif msg.get("role") == "assistant":
            history_messages.append(AIMessage(content=msg.get("content", "")))
            
    # Jika history terlalu panjang, ambil N terakhir saja agar prompt tidak penuh
    history_messages = history_messages[-6:] 

    chain = contextualize_q_prompt | model
    response = await chain.ainvoke({
        "history": history_messages,
        "question": state["question"]
    })
    
    new_question = response.content.strip()
    print(f"\n[Contextualize] Original Question: '{state['question']}'")
    print(f"[Contextualize] Rewritten Question: '{new_question}'")
    logger.info(f"Contextualized question: '{state['question']}' -> '{new_question}'")
    
    return {"question": new_question}

# Node untuk mengambil konteks dari retriever
def retrieve_context_node(retriever: object): # Fungsi pembungkus untuk LangGraph yang menerima retriever
    async def node_func(state: State):
        print(f"Retrieving context for question: {state['question']}")
        # Preprocess question sebelum mengirim ke retriever
        cleaned_question = preprocess_question(state["question"])
        # Panggil metode retriever
        retrieved_docs = retriever.invoke(cleaned_question)

                # --- TAMBAHKAN LOGGING KONTEKS DI SINI ---
        print(f"Retrieved {len(retrieved_docs)} documents.")
        logger.info(f"Retrieved {len(retrieved_docs)} documents for question: '{state['question']}'")
        print(f"retrieved_docs: \n{retrieved_docs}")
        return {"context": retrieved_docs}
    return node_func

# Node untuk menghasilkan jawaban umum berdasarkan konteks
def generate_general_answer(state: State): # Tidak perlu menerima retriever
    print("Generating general answer...")
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    current_date = get_time()

    # Format history menjadi string yang mudah dibaca LLM
    history_text = ""
    if state.get("conversation_history"):
        for msg in state["conversation_history"]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            history_text += f"{role}: {content}\n"
    
    if not history_text:
        history_text = "Belum ada riwayat percakapan."

    chain = general_rag_prompt | model
    response = chain.invoke({ 
        "question": state["question"],
        "context": docs_content,
        "date": current_date,
        "history": history_text
    })
    print("General answer generated.")
    print(f"response: \n{response.content.strip()}")  
    
    # Parse JSON response using Regex for robustness
    try:
        content = response.content.strip()
        # Cari pattern JSON object {...}
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            parsed_response = json.loads(json_str)
            answer = parsed_response.get("answer", "")
            category = parsed_response.get("category", "Umum")
            print("category: ", category)
        else:
            # Jika tidak ada kurung kurawal, asumsikan raw text
            raise ValueError("No JSON object found")

    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse JSON response: {e}. Content: {content[:100]}...")
        # Fallback: Treat entire content as answer
        answer = content
        category = "Umum"
        
    return {"answer": answer, "category": category}

# Node untuk klasifikasi intent
async def classify_intent(state: State):
    print(f"Classifying intent for question: {state['question']}")
    chain = intent_classification_prompt | model
    response = await chain.ainvoke({"question": state["question"]}) 
    intent = response.content.strip().lower()
    if intent not in ['tracking', 'general']:
        intent = 'general' # Fallback
    print(f"Intent classified as: {intent}")
    return {"intent": intent}

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
                return {"answer": result.get('message', "Mohon berikan nomor registrasi."), "intent": "tracking_pending_number", "tracking_data": result.get('tracking_data'), "category": "Tracking"}
            else:
                # Jika agent mengembalikan jawaban tanpa meminta nomor, mungkin karena error parsing
                return {"answer": result.get('message', "Terjadi kesalahan saat memproses permintaan pelacakan."), "intent": "tracking_error", "tracking_data": result.get('tracking_data'), "category": "Tracking"}
        except Exception as e:
            logger.error(f"Error in tracking_agent.process_tracking_request: {e}")
            return {"answer": "Terjadi kesalahan internal saat memproses permintaan pelacakan.", "intent": "tracking_error", "tracking_data": None, "category": "Tracking"}
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
                updated_state['category'] = 'Tracking' # Set kategori untuk tracking
            else:
                # Jika masih meminta nomor (mungkin nomor salah dari agent)
                updated_state['answer'] = result.get('message', "Mohon berikan nomor registrasi yang valid.")
                updated_state['category'] = 'Tracking'
            return updated_state
        except Exception as e:
            logger.error(f"Error in tracking_agent.process_tracking_request with number {number_to_use}: {e}")
            # Kembalikan pesan error, tetapi tetap simpan nomor jika ditemukan
            error_state = {"tracking_data": None}
            if current_tracking_number:
                 error_state['tracking_number'] = current_tracking_number
            error_state['answer'] = "Terjadi kesalahan saat menghubungi sistem pelacakan. Silakan coba lagi nanti."
            error_state['intent'] = "tracking_error"
            error_state['category'] = 'Tracking'
            return error_state


# --- LangGraph Setup ---
def create_conversation_graph(retriever): # Terima retriever sebagai parameter
    graph_builder = StateGraph(State)

    # Tambahkan node-node ke graph
    graph_builder.add_node("classifier", classify_intent)
    graph_builder.add_node("tracking_handler", handle_tracking_intent)
    graph_builder.add_node("contextualize", contextualize_question) # Node baru
    # Gunakan fungsi pembungkus yang membawa retriever
    graph_builder.add_node("retriever", retrieve_context_node(retriever)) 
    graph_builder.add_node("llm_generator", generate_general_answer)

    # Tambahkan edge awal
    graph_builder.add_edge(START, "classifier")

    # Kondisional edge dari classifier
    def route_intent(state):
        intent = state.get("intent", "general")
        if intent in ["tracking", "tracking_pending_number"]: 
            return "tracking_handler"
        else:
            return "contextualize" # Arahkan ke contextualize dulu, bukan langsung retriever

    graph_builder.add_conditional_edges(
        "classifier",
        route_intent,
        {
            "tracking_handler": "tracking_handler",
            "contextualize": "contextualize"
        }
    )
    
    # Alur General: Contextualize -> Retriever -> LLM
    graph_builder.add_edge("contextualize", "retriever")
    graph_builder.add_edge("retriever", "llm_generator")
    
    # Alur Tracking: Selesai di handler
    graph_builder.add_edge("tracking_handler", END)
    
    graph_builder.add_edge("llm_generator", END)

    graph = graph_builder.compile()
    logger.info("LangGraph compiled.")
    print("LangGraph compiled.")
    return graph