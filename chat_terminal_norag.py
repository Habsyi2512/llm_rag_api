import sys
import os

# Menambahkan root directory ke sys.path agar bisa import module 'app'
# walau dijalankan langsung dari terminal
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import get_llm_model
from langchain_core.messages import HumanMessage

def main():
    print("=====================================================")
    print("🤖 Chatbot LLM (Tanpa RAG / Kosong) - Mode Terminal")
    print("Ketik 'exit' atau 'keluar' untuk mengakhiri percakapan.")
    print("=====================================================\n")

    try:
        print("Menginisialisasi model LLM...")
        llm = get_llm_model()
        print("Model berhasil dimuat! Silakan mulai bertanya.\n")
    except Exception as e:
        print(f"Gagal memuat model LLM: {e}")
        return

    while True:
        try:
            user_input = input("Anda: ")
            
            # Cek perintah keluar
            if user_input.lower() in ['exit', 'keluar', 'quit']:
                print("Menutup sesi chat. Sampai jumpa!")
                break
            
            # Cek jika input kosong
            if not user_input.strip():
                continue

            print("Bot (Tanpa RAG) sedang mengetik...")
            
            # Memanggil LLM secara langsung tanpa menyisipkan RAG/Konteks
            response = llm.invoke([HumanMessage(content=user_input)])
            
            print(f"Bot : {response.content}\n")

        except KeyboardInterrupt:
            print("\nMenutup sesi chat. Sampai jumpa!")
            break
        except Exception as e:
            print(f"\nTerjadi kesalahan: {e}\n")

if __name__ == "__main__":
    main()
