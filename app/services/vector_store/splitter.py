# app/services/vector_store/splitter.py

from typing import List, Dict, Iterable
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
import logging

logger = logging.getLogger(__name__)

DEFAULT_SPLITTER = {
    "chunk_size": 1800,
    "chunk_overlap": 400
}

def pre_split_by_marker(text: str) -> List[str]:
    """
    Pisahkan dokumen berdasarkan tanda ### (delimiter manual).
    Misalnya di dokumen kamu:
    ### KARTU KELUARGA
    ### KTP ELEKTRONIK
    dll.
    """
    parts = re.split(r'\n?#{3,}\s*', text)
    # Bersihkan bagian kosong & whitespace
    parts = [p.strip() for p in parts if p.strip()]
    return parts


def clean_text(text: str) -> str:
    """
    Membersihkan teks dari whitespace berlebih dan newline yang tidak perlu.
    Menggabungkan baris yang terputus menjadi satu paragraf yang mengalir.
    """
    if not text:
        return ""
    # Mengganti semua whitespace (newline, tab, spasi ganda) dengan satu spasi
    return re.sub(r'\s+', ' ', text).strip()




def split_text_by_pasal(text: str) -> List[str]:
    """
    Memecah teks peraturan perundang-undangan berdasarkan Pasal.
    Strategi:
    1. Gunakan Newline sebagai indikator utama Header Pasal.
    2. Regex mencari pola: (Newline atau Awal String) + "Pasal" + Angka.
    """
    chunks = []
    
    # Pola untuk menemukan Header Pasal:
    # (?:\n|^)      -> Non-capturing group: Newline ATAU Awal String
    # \s*           -> Optional whitespace
    # (Pasal\s+\d+) -> Group 1: "Pasal 1", "Pasal 20", dst.
    # \s+           -> Whitespace setelah angka (memastikan bukan "Pasal 10" jika kita cari "Pasal 1")
    #
    # Kita gunakan re.split dengan capturing group agar delimiter (Pasal X) juga dikembalikan.
    
    # 1. Split berdasarkan Header Pasal
    # Pattern: \n\s*Pasal\s+\d+\s
    # Kita gunakan lookahead/lookbehind atau sekadar split dan re-assemble.
    
    # Cara paling aman: Split by pattern, lalu gabungkan Header dengan Contentnya.
    pattern = r'(?:^|\n)\s*(Pasal\s+\d+)\s+'
    
    parts = re.split(pattern, text, flags=re.IGNORECASE)
    
    # parts[0] adalah teks sebelum Pasal pertama (bisa jadi kosong atau konsiderans/pembukaan)
    # parts[1] adalah Header Pasal 1 (misal "Pasal 1")
    # parts[2] adalah Isi Pasal 1
    # parts[3] adalah Header Pasal 2
    # parts[4] adalah Isi Pasal 2
    # dst...
    
    # Jika ada teks pembuka (parts[0]), kita bisa simpan atau abaikan. 
    # Untuk RAG, biasanya kita butuh Pasal.
    
    current_chunk = ""
    
    # Mulai iterasi dari index 1
    for i in range(1, len(parts), 2):
        header = parts[i].strip()      # "Pasal 1"
        content = parts[i+1].strip()   # "Dalam peraturan ini..."
        
        # Gabungkan dan bersihkan
        full_text = f"{header} {content}"
        
        # Normalisasi whitespace (merge lines) HANYA setelah splitting selesai
        clean_chunk = re.sub(r'\s+', ' ', full_text).strip()
        
        if clean_chunk:
            chunks.append(clean_chunk)
            
    return chunks

def split_documents_to_chunks(
    docs: Iterable[Dict],
    chunk_size: int = None,
    chunk_overlap: int = None
) -> List[Document]:
    """
    docs: iterable of dict dengan key:
      - doc_id atau faq_id
      - content
      - metadata (opsional)
    """
    chunk_size = chunk_size or DEFAULT_SPLITTER["chunk_size"]
    chunk_overlap = chunk_overlap or DEFAULT_SPLITTER["chunk_overlap"]

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    result = []

    for doc in docs:
        content = doc.get("content") or ""
        base_meta = dict(doc.get("metadata", {}))
        data_source = base_meta.get("source", "")
        title = base_meta.get("title", "").lower()

        # Deteksi apakah ini dokumen regulasi (Perpres, Permendagri, UU, dll)
        # Bisa cek dari Title atau Content
        is_regulation = "peraturan" in title or "undang-undang" in title or "keputusan" in title or "perpres" in title or "permendagri" in title
        
        # Cek juga kontennya jika title tidak jelas
        if not is_regulation and re.search(r'Pasal\s+\d+', content[:5000]): # Cek 5000 karakter pertama
             is_regulation = True

        if is_regulation:
            logger.info(f"Document detected as Regulation (Pasal-based): {title or data_source}")
            # Gunakan strategi splitting khusus Pasal
            pasal_chunks = split_text_by_pasal(content)
            
            if pasal_chunks:
                logger.info(f"Successfully split into {len(pasal_chunks)} Pasal chunks.")
                for chunk_text in pasal_chunks:
                    # Kita bisa memperkaya metadata di sini jika mau (misal ekstrak nomor pasal)
                    # Untuk sekarang, simpan sebagai chunk utuh
                    
                    # Jika satu pasal sangat panjang (lebih dari chunk_size), 
                    # kita tetap perlu memecahnya lagi dengan text_splitter biasa
                    if len(chunk_text) > chunk_size:
                        sub_chunks = text_splitter.split_text(chunk_text)
                        for sub_chunk in sub_chunks:
                            result.append(Document(page_content=sub_chunk, metadata=base_meta))
                    else:
                        result.append(Document(page_content=chunk_text, metadata=base_meta))
                continue # Lanjut ke dokumen berikutnya, skip logic default
            else:
                logger.warning("Regulation detected but failed to split by Pasal. Fallback to default splitter.")

        # --- Default Logic (Existing) ---

        # Gunakan regex untuk deteksi yang lebih robust (menangani variasi newline dsb)
        if re.search(r'#{3,}', content):
            logger.info(f"Detected manual delimiter ### in document from source: {data_source}")
            sections = pre_split_by_marker(content)
        else:
            sections = [content]

        for section in sections:
            # Bersihkan teks sebelum di-split menjadi chunks
            cleaned_section = clean_text(section)
            if not cleaned_section:
                continue
                
            chunks = text_splitter.split_text(cleaned_section)
            for chunk in chunks:
                meta = dict(base_meta)
                result.append(Document(page_content=chunk, metadata=meta))

    return result
