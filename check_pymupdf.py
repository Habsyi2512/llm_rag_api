try:
    import fitz
    print("PyMuPDF (fitz) is available!")
    print(f"Version: {fitz.__doc__}")
except ImportError as e:
    print(f"PyMuPDF not found: {e}")

try:
    from langchain_community.document_loaders import PyMuPDFLoader
    print("PyMuPDFLoader is importable from langchain_community")
except ImportError as e:
    print(f"PyMuPDFLoader import failed: {e}")
