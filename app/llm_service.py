import os, re
from langchain.chat_models import init_chat_model
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing_extensions import List, TypedDict

from langgraph.graph import START, StateGraph

# Impor dari modul lokal
from .config import GOOGLE_API_KEY, PDF_PATH, GOOGLE_SPREADSHEET_ID
from .utils.prompt_template import prompt_template
from .utils.load_csv_from_url import load_csv_from_url
from .utils.get_time import get_time

print("Initializing LLM model...")
model = init_chat_model(
    model="gemini-2.0-flash",
    model_provider="google_genai",
    google_api_key=GOOGLE_API_KEY
)
print("LLM model initialized.")

print("Initializing embeddings model...")
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=GOOGLE_API_KEY
)
print("Embeddings model initialized.")

CHROMA_PERSIST_DIR = "./chroma_langchain_db"
CHROMA_COLLECTION_NAME = "chatbot_lokal"

print("Initializing vector store...")
try:
    vector_store = Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )
    if vector_store._collection.count() == 0:
        raise FileNotFoundError("Vector store is empty.")
    print(f"Loaded existing vector store with {vector_store._collection.count()} documents.")
except Exception as e:
    print(f"Failed to load vector store: {e}. Creating a new one from PDF...")

    # Validasi keberadaan file PDF
    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF tidak ditemukan di {PDF_PATH}.")

    # Muat dan split PDF
    print("Memuat dokumen PDF...")
    loader = PyPDFLoader(PDF_PATH)
    pdf_docs = loader.load()
    print(f"Loaded {len(pdf_docs)} halaman dari PDF.")

    print("Melakukan pemotongan (chunking) dokumen PDF...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=300)
    pdf_splits = text_splitter.split_documents(pdf_docs)

    # Muat CSV dari Google Sheets
    print("Memuat data CSV dari Google Sheets...")
    csv_docs = load_csv_from_url(GOOGLE_SPREADSHEET_ID)

    print("Melakukan pemotongan (chunking) dokumen CSV...")
    csv_splits = text_splitter.split_documents(csv_docs)

    # Gabungkan semua dokumen hasil split
    combined_docs = pdf_splits + csv_splits
    print(f"Total dokumen yang akan diindeks: {len(combined_docs)}")

    # Buat ulang vector store
    vector_store = Chroma.from_documents(
        documents=combined_docs,
        embedding=embeddings,
        collection_name=CHROMA_COLLECTION_NAME,
        persist_directory=CHROMA_PERSIST_DIR,
    )
    print("Vector store berhasil dibuat dan disimpan.")


class State(TypedDict):
    question: str
    context: List[Document]
    answer: str

def refresh_csv_data():
    print("Refreshing CSV data...")
    
    # Hapus semua dokumen lama yang berasal dari CSV
    try:
        vector_store._collection.delete(
            where={"metadata.source": "csv"}
        )
    except Exception as e:
        print(f"Failed to delete old CSV docs: {e}")

    # Muat data CSV terbaru
    new_csv_docs = load_csv_from_url(GOOGLE_SPREADSHEET_ID)

    # Tambahkan metadata agar bisa dibedakan
    for doc in new_csv_docs:
        if not doc.metadata:
            doc.metadata = {}
        doc.metadata["source"] = "csv"

    vector_store.add_documents(new_csv_docs)
    print(f"Added {len(new_csv_docs)} fresh CSV documents.")

def preprocess_question(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s\+\-\*/=]', '', text) 
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def retrieve_context(state: State):
    print(f"Retrieving context for question: {state['question']}")
    # refresh_csv_data()

    cleaned_question = preprocess_question(state['question'])
    retrieved_docs = vector_store.similarity_search(cleaned_question, k=3)
    print(f"Retrieved {len(retrieved_docs)} documents.")
    return {"context": retrieved_docs}

def generate_answer(state: State):
    print("Generating answer...")
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    current_date = get_time()

    chain = prompt_template | model
    response = chain.invoke({
        "question": state["question"],
        "context": docs_content,
        "date": current_date
    })
    print("Answer generated.")
    return {"answer": response.content}

print("Compiling LangGraph...")
graph_builder = StateGraph(State)

graph_builder.add_node("retriever", retrieve_context)
graph_builder.add_node("llm_generator", generate_answer)

graph_builder.add_edge(START, "retriever")
graph_builder.add_edge("retriever", "llm_generator")

graph = graph_builder.compile()
print("LangGraph compiled.")

def process_question(question: str) -> str:
    state = graph.invoke({"question": question})
    answer = str(state['answer']).lower()
    return answer