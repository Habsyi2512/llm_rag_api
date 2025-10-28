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
      - id atau faq_id
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
        doc_id = doc.get("id") or doc.get("faq_id")

        # Jika teks panjang dan mengandung marker ###
        if "###" in content:
            sections = pre_split_by_marker(content)
        else:
            sections = [content]

        for section_idx, section in enumerate(sections):
            # Split ulang tiap section jika terlalu panjang
            chunks = text_splitter.split_text(section)
            section_title = section.split("\n", 1)[0][:100]  # ambil judul atau baris pertama
            for idx, chunk in enumerate(chunks):
                meta = dict(base_meta)
                meta.update({
                    "doc_id": doc_id,
                    "section_index": str(section_idx),
                    "section_title": section_title
                })
                result.append(Document(page_content=chunk, metadata=meta))

    return result
