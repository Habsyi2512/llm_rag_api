import asyncio
import json
import pandas as pd
from bert_score import score, model2layers

# Import fungsi-fungsi dari sistemmu
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.startup import get_graph, init_graph
from app.models.state import State

# Setup logging optional
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pastikan model dikenali (gunakan model multilingual aman)
model2layers["xlm-roberta-base"] = 12


# === 1. Dataset Pertanyaan dan Referensi ===
pertanyaan = [
    "Apa yang dimaksud dengan KTP-el?",
    "Apa fungsi dari SIAK (Sistem Informasi Administrasi Kependudukan)?",
    "Siapa yang wajib memiliki Surat Keterangan Pindah (SKP)?",
    "Apa Tugas Pokok Disdukcapil Kepulauan Anambas?",
    "Apa persyaratan pembuatan kartu keluarga yang rusak?",
    "Apa Syarat yang Diperlukan untuk Pembuatan KTP?",
    "Jika Saya ingin membuat SKPWNI, bagaimana mekanisme atau prosedurnya?",
    "Apa Motto Pelayanan Disdukcapil Kepulauan Anambas?",
    "Apa Persyaratan Pembuatan Akta Kelahiran?",
    "Siapa Bupati Kabupaten Kepulauan Anambas tahun 2024?"
]

refs = [
    "Kartu Tanda Penduduk Elektronik (KTP-el) adalah kartu tanda penduduk yang dilengkapi dengan cip yang merupakan identitas resmi penduduk sebagai bukti diri yang diterbitkan oleh Disdukcapil Kabupaten/Kota.",
    "Sistem Informasi Administrasi Kependudukan (SIAK) adalah sistem informasi yang memanfaatkan teknologi informasi dan komunikasi untuk memfasilitasi pengelolaan informasi Administrasi Kependudukan di tingkat penyelenggara dan Disdukcapil Kabupaten/Kota sebagai satu kesatuan.",
    "Surat Keterangan Pindah (SKP) adalah surat keterangan yang wajib dimiliki oleh Penduduk yang bermaksud pindah ke kabupaten/kota/provinsi lain, yang diterbitkan oleh Disdukcapil Kabupaten/Kota atau unit pelaksana dinas kependudukan dan pencatatan sipil dari daerah asal.",
    "Melaksanakan urusan pemerintahan yang menjadi kewenangan daerah di bidang administrasi kependudukan dan pencatatan sipil dan tugas pembantuan yang diberikan kepada daerah",
    "Mengisi Formulir; Surat Keterangan Hilang Dari Kepolisian; Fotocopy KTP-el; KK Yang Rusak",
    "Persyaratan dalam pembuatan KTP Elektronik yaitu: Fotokopi Kartu Keluarga (KK); KTP-el asli (Bagi KTP-el yang rusak); Surat keterangan kehilangan dari kepolisian (Bagi KTP-el yang hilang)",
    "Menuju ke front office untuk mengisi buku tamu, mengambil nomor antrian, menyerahkan berkas persyaratan; Menunggu panggilan; Petugas memberikan resi pengambilan; Menuju ke front office untuk pengambilan hasil SKPWNI",
    "Disdukcapil Kepulauan Anambas memiliki motto BERMADAH: Bersih, Efisien, Responsif, Mudah, Akuntabel, Dedikasi, Amanah, Hormat",
    "Persyaratan Akta Kelahiran: Surat keterangan lahir dari fasilitas kesehatan; Fotokopi KK orang tua; Fotokopi KTP orang tua; Fotokopi buku nikah atau akta perkawinan",
    "Maaf, saya tidak menemukan informasi tersebut dalam data yang saya miliki."
]


# === 2. Fungsi untuk menghasilkan jawaban dari sistem chatbot ===
async def generate_answers():
    graph = get_graph()
    if not graph:
        print("⚙️ Graph belum ada, melakukan init_graph()...")
        await init_graph()  # inisialisasi manual
        graph = get_graph()

    if not graph:
        raise RuntimeError("Graph belum siap, pastikan sistem LLM kamu sudah diinisialisasi.")

    preds = []
    for q in pertanyaan:
        state: State = {
            "question": q,
            "context": [],
            "answer": "",
            "conversation_history": [],
            "user_id": "test_evaluation",
            "intent": "unknown",
            "tracking_number": None,
            "tracking_data": None
        }

        try:
            final_state = await graph.ainvoke(state)
            answer = final_state.get("answer", "Maaf, belum bisa menjawab.")
            preds.append(answer)
            logger.info(f"✅ Q: {q}\n→ A: {answer}\n")
        except Exception as e:
            logger.error(f"❌ Error saat memproses '{q}': {e}")
            preds.append("Error saat memproses jawaban.")
    
    return preds


# === 3. Fungsi utama evaluasi BERTScore ===
async def main():
    preds = await generate_answers()

    # Hitung skor kesamaan semantik
    P, R, F1 = score(preds, refs, lang="id", model_type="xlm-roberta-base")

    data = {
        "Pertanyaan": pertanyaan,
        "Jawaban Chatbot": preds,
        "Referensi": refs,
        "Precision": [p.item() for p in P],
        "Recall": [r.item() for r in R],
        "F1 Score": [f.item() for f in F1]
    }

    df = pd.DataFrame(data)
    print("\n=== Hasil Evaluasi Chatbot (BERTScore) ===\n")
    print(df[["Pertanyaan", "Precision", "Recall", "F1 Score"]])

    print("\nRata-rata Skor:")
    print(f"Precision: {P.mean().item():.4f}")
    print(f"Recall: {R.mean().item():.4f}")
    print(f"F1 Score: {F1.mean().item():.4f}")

    # Simpan ke CSV jika ingin dokumentasi hasil penelitian
    df.to_csv("hasil_evaluasi_chatbot2.csv", index=False, encoding="utf-8-sig")
    print("\n✅ Hasil evaluasi disimpan ke 'hasil_evaluasi_chatbot2.csv'")


if __name__ == "__main__":
    asyncio.run(main())
