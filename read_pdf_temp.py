from pypdf import PdfReader
import sys

# Set stdout to utf-8 to handle special characters
sys.stdout.reconfigure(encoding='utf-8')

try:
    reader = PdfReader("/Users/muhammadhabsyimubarak/Desktop/proyek-profesional/project/llm_rag_gemini_api/app/data/Permendagri-Nomor-108-Tahun-2019.pdf")
    # Read first 5 pages to get enough context for 3 questions
    text = ""
    for i in range(min(5, len(reader.pages))):
        page = reader.pages[i]
        text += page.extract_text() + "\n"
    
    print(text)
except Exception as e:
    print(f"Error reading PDF: {e}")
