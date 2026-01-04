from langchain_community.document_loaders import PyPDFLoader
import sys

try:
    loader = PyPDFLoader("/Users/muhammadhabsyimubarak/Desktop/proyek-profesional/project/cms-dukcapil/database/documents/Perpres-Nomor-96-Tahun-2018.pdf")
    docs = loader.load()
    
    total_text = ""
    for doc in docs:
        total_text += doc.page_content
        
    print(f"Total characters extracted: {len(total_text)}")
    print("Preview (first 500 chars):")
    print(total_text[:500])
    
    if len(total_text.strip()) < 100:
        print("\nWARNING: Very little text extracted. The PDF might be a scan (images).")
        
except Exception as e:
    print(f"Error: {e}")
