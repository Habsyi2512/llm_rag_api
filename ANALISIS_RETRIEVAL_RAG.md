# Analisis Proses Retrieval RAG pada Project `llm_rag_gemini_api`

Dokumen ini menjelaskan alur retrieval pada project `llm_rag_gemini_api` berdasarkan kode yang ada di repository. Fokus analisis berada pada bagaimana knowledge base diambil, diproses menjadi chunk, diubah menjadi embedding, disimpan ke vector store, dicari kembali oleh retriever, lalu dimasukkan ke prompt LLM.

## 1. Struktur Folder dan File Utama RAG

Struktur utama yang berhubungan langsung dengan RAG adalah:

```text
llm_rag_gemini_api/
├── app/
│   ├── chains/
│   │   └── conversation_chain.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── startup.py
│   ├── models/
│   │   ├── domain.py
│   │   └── state.py
│   ├── routers/
│   │   ├── chat_routes.py
│   │   ├── dashboard_routes.py
│   │   └── vector_routes.py
│   ├── services/
│   │   ├── api_client.py
│   │   ├── embedding_service.py
│   │   ├── llm_service.py
│   │   └── vector_store/
│   │       ├── base.py
│   │       ├── crud.py
│   │       ├── fetcher.py
│   │       ├── splitter.py
│   │       └── vector_store_service.py
│   └── utils/
│       ├── helpers.py
│       └── prompt_templates.py
├── rag_database.db
├── vector_store_db_llm_rag/
│   └── chroma.sqlite3
├── faq.csv
├── faqs.json
└── requirements.txt
```

Peran file utama:

- `app/services/vector_store/vector_store_service.py`: pusat proses indexing dan retrieval setup. File ini menginisialisasi embedding model, membuat koneksi Chroma, refresh knowledge base, memproses PDF, dan membuat hybrid retriever.
- `app/services/vector_store/splitter.py`: preprocessing dan chunking dokumen.
- `app/services/vector_store/fetcher.py`: mengambil data FAQ dan dokumen dari database lokal.
- `app/services/vector_store/crud.py`: memasukkan, menghapus, dan memperbarui chunk di Chroma.
- `app/services/embedding_service.py`: membuat model embedding berbasis Ollama.
- `app/chains/conversation_chain.py`: alur LangGraph untuk intent classification, contextualization, retrieval, dan generation.
- `app/utils/prompt_templates.py`: template prompt yang menerima konteks hasil retrieval.
- `app/routers/chat_routes.py`: endpoint chat yang memanggil graph RAG.
- `app/routers/vector_routes.py` dan `app/routers/dashboard_routes.py`: endpoint sinkronisasi data FAQ/dokumen ke vector store.
- `app/core/startup.py`: inisialisasi database, vector store, retriever, dan graph saat aplikasi berjalan.

## 2. Sumber Dokumen, FAQ, dan Knowledge Base

Knowledge base utama berasal dari database lokal melalui model SQLAlchemy:

- FAQ: tabel `faqs`, model `Faq` di `app/models/domain.py`.
- Dokumen: tabel `documents`, model `Document` di `app/models/domain.py`.
- File fisik PDF: path atau URL disimpan di kolom `documents.source_path`.

Potongan kode model:

```python
# app/models/domain.py
class Faq(Base):
    __tablename__ = "faqs"
    id = Column(Integer, primary_key=True, index=True)
    question = Column(String(255), nullable=False)
    answer = Column(Text, nullable=False)

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    source_path = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(JSON, nullable=True)
```

Pengambilan data dilakukan oleh `fetch_all_faqs()` dan `fetch_all_documents()`:

```python
# app/services/vector_store/fetcher.py
async def fetch_all_faqs():
    result = await session.execute(select(Faq))
    faqs = result.scalars().all()
    data.append({
        "id": faq.id,
        "question": faq.question,
        "answer": faq.answer
    })

async def fetch_all_documents():
    result = await session.execute(select(Document))
    docs = result.scalars().all()
    data.append({
        "id": doc.id,
        "title": doc.title,
        "source_path": doc.source_path,
        "content": doc.content,
        "metadata": doc.metadata_json
    })
```

Selain database, repository juga memiliki `faq.csv`, `faqs.json`, dan file di `app/data/`, tetapi alur RAG aktif pada kode menggunakan database lokal dan `source_path` PDF, bukan langsung membaca file CSV/JSON tersebut.

## 3. Preprocessing, Chunking, dan Embedding

### 3.1 Normalisasi FAQ

Saat refresh vector store, FAQ dari database diubah menjadi teks:

```python
# app/services/vector_store/vector_store_service.py
question = f.get("question", "").strip()
answer = f.get("answer", "").strip()
content = f"pertanyaan: {question}\njawaban: {answer}".strip()
combined_full_docs.append({
    "content": content,
    "metadata": {
        "source": "faq",
        "faq_id": str(f.get("id", "")),
    }
})
```

Pada endpoint dashboard, formatnya sedikit berbeda:

```python
# app/routers/dashboard_routes.py
content = f"Q: {new_faq.question}\nA: {new_faq.answer}"
background_tasks.add_task(
    add_faq_to_vector_store,
    content=content,
    metadata={"faq_id": str(new_faq.id), "type": "faq"}
)
```

### 3.2 Ekstraksi PDF

Dokumen PDF diproses dari `source_path`. Jika path lokal tersedia, file langsung digunakan. Jika bukan path lokal, kode menganggapnya sebagai URL atau path publik Laravel:

```python
# app/services/api_client.py
async def download_file_to_temp(relative_url: str, suffix: str = ".pdf") -> str:
    if os.path.exists(relative_url):
        return relative_url

    if relative_url.startswith("public/"):
        corrected_url_path = relative_url.replace('public/', 'storage/')
        full_url = f"{settings.LARAVEL_PUBLIC_URL}/{corrected_url_path}"
```

PDF kemudian diekstrak memakai `PyMuPDFLoader`:

```python
# app/services/vector_store/vector_store_service.py
async def _download_pdf_and_get_chunks(pdf_url: str, metadata: Dict) -> List:
    temp_path = await download_file_to_temp(pdf_url, suffix=".pdf")

    def sync_load_pdf():
        loader = PyMuPDFLoader(temp_path)
        return loader.load()

    documents = await asyncio.to_thread(sync_load_pdf)
    full_text = ""
    for doc in documents:
        full_text += doc.page_content + "\n"

    chunks = split_documents_to_chunks(combined)
    return chunks
```

### 3.3 Preprocessing Teks

Preprocessing dasar dilakukan oleh `clean_text()`:

```python
# app/services/vector_store/splitter.py
def clean_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()
```

Artinya newline, tab, dan spasi berulang digabung menjadi satu spasi.

### 3.4 Chunking

Default chunking menggunakan `RecursiveCharacterTextSplitter` dengan:

```python
# app/services/vector_store/splitter.py
DEFAULT_SPLITTER = {
    "chunk_size": 1800,
    "chunk_overlap": 400
}
```

Kode pembuatan splitter:

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap
)
```

Project memiliki tiga strategi chunking:

1. Dokumen regulasi dipotong berdasarkan `Pasal`.
2. Dokumen dengan delimiter manual `###` dipotong per section.
3. Dokumen biasa dipotong dengan `RecursiveCharacterTextSplitter`.

Deteksi dokumen regulasi:

```python
is_regulation = (
    "peraturan" in title
    or "undang-undang" in title
    or "keputusan" in title
    or "perpres" in title
    or "permendagri" in title
)

if not is_regulation and re.search(r'Pasal\s+\d+', content[:5000]):
    is_regulation = True
```

Pemotongan berdasarkan pasal:

```python
def split_text_by_pasal(text: str) -> List[str]:
    pattern = r'(?:^|\n)\s*(Pasal\s+\d+)\s+'
    parts = re.split(pattern, text, flags=re.IGNORECASE)

    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        content = parts[i+1].strip()
        full_text = f"{header} {content}"
        clean_chunk = re.sub(r'\s+', ' ', full_text).strip()
        chunks.append(clean_chunk)
```

Jika satu pasal lebih panjang dari `chunk_size`, teks pasal dipecah lagi dengan splitter biasa:

```python
if len(chunk_text) > chunk_size:
    sub_chunks = text_splitter.split_text(chunk_text)
    for sub_chunk in sub_chunks:
        result.append(Document(page_content=sub_chunk, metadata=base_meta))
else:
    result.append(Document(page_content=chunk_text, metadata=base_meta))
```

### 3.5 Embedding

Embedding dibuat oleh Ollama melalui `langchain_ollama.OllamaEmbeddings`:

```python
# app/services/embedding_service.py
embeddings = OllamaEmbeddings(
    model=settings.OLLAMA_EMBEDDING_MODEL_NAME,
    base_url=settings.OLLAMA_BASE_URL
)
```

Konfigurasi default:

```python
# app/core/config.py
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_EMBEDDING_MODEL_NAME = "bge-m3:latest"
```

Embedding tidak dibuat secara manual di kode. Proses embedding dipanggil implisit ketika `Document` dimasukkan ke Chroma melalui LangChain Chroma.

## 4. Penyimpanan Embedding

Embedding disimpan di ChromaDB persisten:

```python
# app/core/config.py
CHROMA_PERSIST_DIR = "./vector_store_db_llm_rag"
CHROMA_COLLECTION_NAME = "faq_document_vector"
```

Koneksi Chroma dibuat di:

```python
# app/services/vector_store/vector_store_service.py
chroma = Chroma(
    embedding_function=embeddings,
    persist_directory=persist_directory,
    collection_name=collection_name,
)
```

Folder storage pada repository:

```text
llm_rag_gemini_api/vector_store_db_llm_rag/chroma.sqlite3
```

Hasil inspeksi workspace saat analisis:

- file Chroma: `vector_store_db_llm_rag/chroma.sqlite3`
- collection: `faq_document_vector`
- jumlah embedding/chunk pada Chroma: `255`
- metric vector index pada metadata Chroma: `l2`

Catatan: tabel relasional `rag_database.db` pada workspace saat analisis berisi `0` FAQ dan `0` dokumen, tetapi Chroma persisten masih memiliki 255 chunk dari proses indexing sebelumnya.

## 5. Pemrosesan Pertanyaan User Menjadi Query

Endpoint chat menerima pesan user di `app/routers/chat_routes.py`, lalu membuat state awal LangGraph:

```python
state: State = {
    "question": request_body.message,
    "context": [],
    "answer": "",
    "conversation_history": langchain_history,
    "user_id": str(current_user.id),
    "intent": "unknown",
    "tracking_number": None,
    "tracking_data": None,
    "category": None,
    "is_eval": False
}

final_state = await graph.ainvoke(state)
```

Sebelum retrieval, alur graph melakukan:

1. Intent classification: menentukan apakah pertanyaan adalah `tracking` atau `general`.
2. Contextualization: jika ada riwayat percakapan, pertanyaan lanjutan dirumuskan ulang menjadi standalone question.
3. Preprocessing query: lowercase dan pembersihan karakter.

Contextualization:

```python
# app/chains/conversation_chain.py
async def contextualize_question(state: State):
    if not state.get("conversation_history"):
        return {}

    history_messages = history_messages[-6:]
    chain = contextualize_q_prompt | model
    response = await chain.ainvoke({
        "history": history_messages,
        "question": state["question"]
    })

    return {"question": new_question}
```

Preprocessing query:

```python
# app/utils/helpers.py
def preprocess_question(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s\+\-\*/=]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text
```

Retriever dipanggil menggunakan query yang sudah dibersihkan:

```python
# app/chains/conversation_chain.py
cleaned_question = preprocess_question(state["question"])
retrieved_docs = retriever.invoke(cleaned_question)
return {"context": retrieved_docs}
```

## 6. Query Diubah Menjadi Embedding

Tidak ada fungsi eksplisit seperti `embed_query()` di kode aplikasi. Query diubah menjadi embedding secara implisit oleh LangChain Chroma saat `retriever.invoke(cleaned_question)` dipanggil pada retriever Chroma.

Alur implisitnya:

1. `retriever.invoke(cleaned_question)` dipanggil.
2. Untuk komponen vector retriever, Chroma memakai `embedding_function` yang diberikan saat inisialisasi.
3. `OllamaEmbeddings` mengirim query ke Ollama embedding model (`bge-m3:latest` secara default).
4. Chroma membandingkan embedding query dengan embedding chunk yang tersimpan.

Bukti bahwa embedding function diberikan ke Chroma:

```python
chroma = Chroma(
    embedding_function=embeddings,
    persist_directory=persist_directory,
    collection_name=collection_name,
)
```

Bukti bahwa embedding model adalah Ollama:

```python
embeddings = OllamaEmbeddings(
    model=settings.OLLAMA_EMBEDDING_MODEL_NAME,
    base_url=settings.OLLAMA_BASE_URL
)
```

## 7. Cara Retriever Mencari Chunk Relevan

Project menggunakan hybrid retriever, bukan hanya vector retriever. Hybrid retriever dibuat di `_create_hybrid_retriever()`:

```python
# app/services/vector_store/vector_store_service.py
async def _create_hybrid_retriever(chroma_client):
    collection_data = await asyncio.to_thread(chroma_client.get)

    documents = []
    for i, text in enumerate(texts):
        if text:
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            documents.append(Document(page_content=text, metadata=meta))

    chroma_retriever = chroma_client.as_retriever(search_kwargs={"k": 4})

    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = 4

    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, chroma_retriever],
        weights=[0.3, 0.7]
    )
    return ensemble_retriever
```

Komponen retrieval:

- BM25 Retriever: mencari kecocokan keyword/leksikal dari semua dokumen yang diambil dari Chroma.
- Chroma Vector Retriever: mencari chunk berdasarkan kedekatan embedding.
- EnsembleRetriever: menggabungkan hasil BM25 dan vector search dengan bobot `0.3` untuk BM25 dan `0.7` untuk vector search.

Jika pembuatan BM25 gagal atau tidak ada dokumen, kode fallback ke vector retriever:

```python
if not documents:
    return chroma_retriever

except Exception:
    return chroma_client.as_retriever()
```

## 8. Metode Similarity atau Distance

Pada kode aplikasi, tidak ada konfigurasi eksplisit seperti `cosine`, `dot product`, atau `ip`. Kode hanya membuat Chroma tanpa `collection_metadata`:

```python
Chroma(
    embedding_function=embeddings,
    persist_directory=persist_directory,
    collection_name=collection_name,
)
```

Berdasarkan metadata Chroma yang tersimpan di `vector_store_db_llm_rag/chroma.sqlite3`, vector index collection menggunakan:

```text
space: l2
```

Jadi, untuk vector search pada kondisi workspace ini, metode jarak yang digunakan oleh Chroma adalah `l2` distance. Di atas vector search tersebut, project juga menggunakan BM25 untuk pencarian keyword. Hasil keduanya digabung oleh `EnsembleRetriever`.

Ringkasnya:

- Vector retrieval: Chroma vector search dengan metric `l2` pada collection yang tersimpan.
- Keyword retrieval: BM25.
- Hybrid fusion: `EnsembleRetriever` dengan bobot BM25 `0.3` dan Chroma `0.7`.

## 9. Nilai `top_k`

Nilai jumlah chunk yang diambil diatur di `_create_hybrid_retriever()`:

```python
chroma_retriever = chroma_client.as_retriever(search_kwargs={"k": 4})
bm25_retriever.k = 4
```

Artinya:

- Chroma vector retriever mengambil `k = 4` chunk.
- BM25 retriever juga mengambil `k = 4` chunk.
- Hasil akhir `EnsembleRetriever` dapat berisi gabungan/reranking dari kedua retriever. Secara konsep, jumlah kandidat berasal dari masing-masing retriever sebanyak 4, lalu digabung oleh ensemble.

## 10. Hasil Retrieval Masuk ke Prompt LLM

Hasil retrieval disimpan ke state dengan key `context`:

```python
retrieved_docs = retriever.invoke(cleaned_question)
return {"context": retrieved_docs}
```

Pada node generation, isi dokumen digabung menjadi string:

```python
def generate_general_answer(state: State):
    docs_content = "\n\n".join(doc.page_content for doc in state["context"])
```

String tersebut dikirim ke prompt:

```python
response = chain.invoke({
    "question": state["question"],
    "context": docs_content,
    "date": current_date,
    "history": history_text
})
```

Template prompt memasukkan konteks pada bagian:

```python
# app/utils/prompt_templates.py
Riwayat Percakapan:
{history}

Konteks:
{context}
```

Prompt juga memerintahkan model untuk tidak memakai informasi di luar konteks:

```text
JANGAN gunakan informasi di luar konteks yang diberikan.
Jika informasi tidak ada di konteks, KATAKAN TIDAK TAHU.
```

## 11. Perbedaan Retrieval dan Generation

Bagian retrieval adalah bagian yang bertugas mencari informasi relevan dari knowledge base. Pada project ini, retrieval mencakup:

- preprocessing query;
- embedding query secara implisit melalui Chroma;
- pencarian keyword BM25;
- pencarian vector Chroma;
- penggabungan hasil dengan `EnsembleRetriever`;
- penyimpanan hasil chunk ke `state["context"]`.

File dan fungsi retrieval:

- `app/chains/conversation_chain.py`: `retrieve_context_node()`
- `app/services/vector_store/vector_store_service.py`: `_create_hybrid_retriever()`, `initialize_vector_store()`
- `app/services/vector_store/splitter.py`: `split_documents_to_chunks()`
- `app/services/embedding_service.py`: `get_embeddings_model()`

Bagian generation adalah bagian yang menghasilkan jawaban natural language dari LLM berdasarkan context hasil retrieval. Pada project ini, generation mencakup:

- penggabungan chunk menjadi `docs_content`;
- penyusunan prompt dengan `{context}`, `{question}`, `{history}`, dan `{date}`;
- pemanggilan LLM;
- parsing output JSON untuk mengambil `answer` dan `category`.

File dan fungsi generation:

- `app/chains/conversation_chain.py`: `generate_general_answer()`
- `app/utils/prompt_templates.py`: `general_rag_prompt`, `evaluation_rag_prompt`
- `app/services/llm_service.py`: `get_llm_model()`

Pemisahan alur pada LangGraph:

```python
# app/chains/conversation_chain.py
graph_builder.add_edge("contextualize", "retriever")
graph_builder.add_edge("retriever", "llm_generator")
```

Artinya query dibuat mandiri terlebih dahulu, lalu retrieval mengambil konteks, kemudian generation menghasilkan jawaban.

## 12. Alur RAG End-to-End Berdasarkan Kode

### 12.1 Saat Aplikasi Startup

```python
# app/core/startup.py
await init_db()
await initialize_vector_store(
    force_refresh=False,
    persist_directory=settings.CHROMA_PERSIST_DIR,
    collection_name=settings.CHROMA_COLLECTION_NAME,
)
retriever = get_retriever()
_graph = create_conversation_graph(retriever)
```

Penjelasan:

1. Database diinisialisasi.
2. Embedding model Ollama dibuat.
3. Chroma dibuat atau dikoneksikan ke folder persisten.
4. Jika Chroma kosong, data di-refresh dari database.
5. Hybrid retriever dibuat.
6. LangGraph conversation graph dibuat.

### 12.2 Saat Refresh Vector Store

```python
faqs_response = await fetch_all_faqs()
docs_response = await fetch_all_documents()
```

FAQ dinormalisasi menjadi teks, dokumen PDF diunduh/dibaca, teks PDF diekstrak, semua data dipecah menjadi chunk, lalu dimasukkan ke Chroma:

```python
faq_chunks = split_documents_to_chunks(combined_full_docs)
final_chunks = faq_chunks + processed_chunks
await crud_add_documents(final_chunks)
state.retriever = await _create_hybrid_retriever(chroma)
```

### 12.3 Saat User Bertanya

```python
final_state = await graph.ainvoke(state)
```

Graph menjalankan alur:

```text
START
  -> classifier
  -> contextualize
  -> retriever
  -> llm_generator
  -> END
```

Untuk pertanyaan tracking, graph masuk ke `tracking_handler`, bukan RAG umum.

### 12.4 Saat Retrieval

```python
cleaned_question = preprocess_question(state["question"])
retrieved_docs = retriever.invoke(cleaned_question)
return {"context": retrieved_docs}
```

Retriever yang dipanggil adalah hybrid retriever:

```python
EnsembleRetriever(
    retrievers=[bm25_retriever, chroma_retriever],
    weights=[0.3, 0.7]
)
```

### 12.5 Saat Generation

```python
docs_content = "\n\n".join(doc.page_content for doc in state["context"])
response = chain.invoke({
    "question": state["question"],
    "context": docs_content,
    "date": current_date,
    "history": history_text
})
```

LLM kemudian menghasilkan JSON:

```json
{
  "answer": "Jawaban...",
  "category": "KTP/KK/Akta Kelahiran/Akta Kematian/KIA/Pindah Datang/Umum"
}
```

## Catatan Teknis Penting

1. Konfigurasi default `LLM_PROVIDER` di `app/core/config.py` adalah `google_genai`, sedangkan `app/services/llm_service.py` hanya menerima provider `google` atau `ollama`. Jika `.env` tidak mengubah nilai tersebut, fungsi `get_llm_model()` akan masuk ke error `Unsupported LLM_PROVIDER`.
2. Kode tidak mengatur metric Chroma secara eksplisit. Metric `l2` berasal dari metadata collection Chroma yang sudah tersimpan di folder `vector_store_db_llm_rag`.
3. Embedding menggunakan Ollama, bukan Gemini. Gemini/Google digunakan untuk LLM generation jika provider diset ke `google`.
4. Refresh penuh menghapus isi collection lama lalu melakukan upsert ulang semua chunk.
5. Untuk update FAQ/dokumen, strategi yang dipakai adalah delete chunk lama berdasarkan metadata (`faq_id` atau `doc_id`) lalu insert chunk baru.

## Versi Akademik untuk Laporan Skripsi

Pada sistem chatbot ini, mekanisme Retrieval-Augmented Generation (RAG) diterapkan dengan memisahkan proses pencarian pengetahuan dan proses pembangkitan jawaban. Knowledge base sistem berasal dari data FAQ dan dokumen yang tersimpan di database lokal. Data FAQ diambil dari tabel `faqs`, sedangkan data dokumen diambil dari tabel `documents`. Untuk dokumen berbentuk PDF, sistem menggunakan nilai `source_path` sebagai lokasi file, baik berupa path lokal maupun URL publik, kemudian mengekstrak teks PDF menggunakan `PyMuPDFLoader`.

Tahap preprocessing dilakukan sebelum data dimasukkan ke vector store. FAQ dinormalisasi menjadi pasangan teks pertanyaan dan jawaban. Dokumen PDF diekstrak menjadi teks penuh, kemudian diproses oleh modul chunking. Sistem menggunakan `RecursiveCharacterTextSplitter` dengan ukuran chunk 1800 karakter dan overlap 400 karakter. Selain chunking umum, sistem memiliki strategi khusus untuk dokumen regulasi, yaitu memecah teks berdasarkan struktur pasal menggunakan pola `Pasal <nomor>`. Strategi ini penting karena dokumen administrasi kependudukan sering berbentuk peraturan perundang-undangan, sehingga pemotongan per pasal menjaga konteks hukum tetap utuh.

Setiap chunk direpresentasikan sebagai objek `Document` LangChain yang berisi `page_content` dan metadata seperti `source`, `faq_id`, `doc_id`, dan `title`. Chunk tersebut kemudian disimpan ke ChromaDB sebagai vector database persisten pada direktori `vector_store_db_llm_rag` dengan nama collection `faq_document_vector`. Model embedding yang digunakan adalah `OllamaEmbeddings` dengan konfigurasi default `bge-m3:latest` melalui Ollama pada `http://localhost:11434`. Proses embedding dilakukan secara implisit oleh Chroma ketika chunk ditambahkan ke vector store.

Pada saat pengguna mengirim pertanyaan, sistem membentuk state percakapan dan menjalankannya melalui LangGraph. Pertama, sistem melakukan klasifikasi intent untuk membedakan pertanyaan umum dan pertanyaan pelacakan dokumen. Untuk pertanyaan umum, sistem melakukan contextualization, yaitu merumuskan ulang pertanyaan lanjutan menjadi pertanyaan mandiri berdasarkan riwayat percakapan. Setelah itu query dibersihkan melalui preprocessing sederhana, yaitu lowercasing, penghapusan karakter non-alfanumerik tertentu, dan normalisasi spasi.

Retrieval dilakukan menggunakan pendekatan hybrid search. Sistem membangun dua retriever, yaitu BM25 retriever untuk pencarian berbasis keyword dan Chroma retriever untuk pencarian berbasis embedding. Chroma retriever dikonfigurasi dengan `k = 4`, sedangkan BM25 juga dikonfigurasi dengan `k = 4`. Kedua retriever digabung menggunakan `EnsembleRetriever` dengan bobot 0,3 untuk BM25 dan 0,7 untuk vector retrieval. Dengan demikian, sistem tidak hanya mengandalkan kemiripan semantik, tetapi juga mempertimbangkan kecocokan kata kunci eksplisit. Berdasarkan metadata Chroma yang tersimpan pada workspace, metric vector index yang digunakan adalah `l2` distance.

Hasil retrieval berupa daftar chunk relevan dimasukkan ke dalam state dengan key `context`. Pada tahap generation, seluruh `page_content` dari chunk hasil retrieval digabung menjadi satu string konteks dan dimasukkan ke dalam prompt LLM. Prompt menginstruksikan model untuk menjawab hanya berdasarkan konteks yang diberikan, menyatakan tidak tahu jika informasi tidak ditemukan, dan menghasilkan output dalam format JSON yang berisi `answer` dan `category`. Dengan cara ini, retrieval bertugas menyediakan bukti atau konteks faktual, sedangkan generation bertugas menyusun jawaban akhir yang dapat dipahami pengguna.

Secara keseluruhan, alur RAG pada project ini dapat diringkas sebagai: data FAQ/dokumen diambil dari database, PDF diekstrak, teks dibersihkan dan dipecah menjadi chunk, chunk diubah menjadi embedding dan disimpan di ChromaDB, pertanyaan pengguna diproses menjadi query, query digunakan untuk hybrid retrieval BM25 dan vector search, hasil retrieval dimasukkan ke prompt LLM, lalu LLM menghasilkan jawaban berbasis konteks.

## Versi Jawaban Singkat untuk Sidang

Proses retrieval pada project saya dimulai dari knowledge base berupa FAQ dan dokumen yang disimpan di database lokal. FAQ diambil dari tabel `faqs`, sedangkan dokumen diambil dari tabel `documents`. Jika dokumen berupa PDF, file dibaca dari `source_path`, kemudian teksnya diekstrak menggunakan `PyMuPDFLoader`.

Setelah itu data diproses menjadi chunk. Untuk teks umum, sistem menggunakan `RecursiveCharacterTextSplitter` dengan `chunk_size` 1800 dan `chunk_overlap` 400. Untuk dokumen regulasi, sistem punya strategi khusus, yaitu memecah dokumen berdasarkan `Pasal`, sehingga konteks hukum tidak terpotong sembarangan.

Setiap chunk kemudian disimpan ke ChromaDB pada folder `vector_store_db_llm_rag` dengan collection `faq_document_vector`. Embedding dibuat menggunakan Ollama, default modelnya `bge-m3:latest`. Saat user bertanya, pertanyaan dibersihkan dulu, lalu dikirim ke retriever.

Retriever yang digunakan adalah hybrid retriever, yaitu gabungan BM25 dan vector search Chroma. BM25 menangkap kecocokan kata kunci, sedangkan Chroma menangkap kemiripan semantik dari embedding. Masing-masing retriever mengambil `k = 4` chunk, lalu digabung memakai `EnsembleRetriever` dengan bobot 0,3 untuk BM25 dan 0,7 untuk vector search. Pada Chroma yang tersimpan di project ini, metric vector index-nya adalah `l2` distance.

Hasil retrieval berupa chunk relevan dimasukkan ke prompt LLM sebagai `{context}`. LLM kemudian menjawab berdasarkan konteks tersebut. Jadi retrieval adalah proses mencari dan mengambil potongan dokumen yang relevan, sedangkan generation adalah proses LLM menyusun jawaban akhir dari potongan dokumen tersebut.

