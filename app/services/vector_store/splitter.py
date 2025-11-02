# app/services/vector_store/splitter.py

from typing import List, Dict, Iterable
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re

DEFAULT_SPLITTER = {
    "chunk_size": 1500,
    "chunk_overlap": 150
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

        if "###" in content:
            print("Detected manual delimiter ### in document from source:", data_source)
            print("doc content preview:", content[:100])
            sections = pre_split_by_marker(content)
        else:
            sections = [content]

        for section in sections:
            chunks = text_splitter.split_text(section)
            for chunk in chunks:
                meta = dict(base_meta)
                result.append(Document(page_content=chunk, metadata=meta))

    return result
