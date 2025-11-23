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

        # Gunakan regex untuk deteksi yang lebih robust (menangani variasi newline dsb)
        if re.search(r'#{3,}', content):
            logger.info(f"Detected manual delimiter ### in document from source: {data_source}")
            # print("doc content preview:", content[:100])
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
