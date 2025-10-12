import pandas as pd
from langchain_core.documents import Document

def load_csv_from_url(url: str) -> list[Document]:
    print("Memuat CSV langsung dari Google Sheets menggunakan pandas...")
    df = pd.read_csv(url)  # langsung tanpa requests
    print(f"CSV dimuat: {len(df)} baris.")

    documents = []
    for _, row in df.iterrows():
        # Gabungkan semua kolom menjadi satu string
        content = "\n".join([f"{col}: {row[col]}" for col in df.columns])
        documents.append(Document(page_content=content))

    return documents
