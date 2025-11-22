import asyncio
import json
import pandas as pd
from bert_score import score, model2layers

# Import fungsi-fungsi dari sistemmu
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
    "Apa Visi Disdukcapil Kepulauan Anambas?",
    "Dimana alamat Disdukcapil Kepulauan Anambas?",
    "Apakah ada biaya yang harus dibayarkan untuk mengurus dokumen kependudukan, khususnya KTP?",
    "Apa Tugas Pokok Disdukcapil Kepulauan Anambas?",
    "Apa persyaratan pembuatan kartu keluarga yang rusak?",
    "Apa Syarat yang Diperlukan untuk Pembuatan KTP?",
    "Jika Saya ingin membuat SKPWNI, bagaimana mekanisme atau prosedurnya?",
    "Apa Motto Pelayanan Disdukcapil Kepulauan Anambas?",
    "Apa Persyaratan Pembuatan Akta Kelahiran?",
    "Siapa Bupati Kabupaten Kepulauan Anambas tahun 2024?"
]

refs = [
    "Terciptanya masyarakat sadar akan tertib administrasi kependudukan.",
    "jl. imam bonjol no. 50, tarempa, kecamatan siantan.",
    "layanan pembuatan ktp elektronik tidak dipungut biaya",
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
    df.to_csv("hasil_evaluasi_chatbot.csv", index=False, encoding="utf-8-sig")
    print("\n✅ Hasil evaluasi disimpan ke 'hasil_evaluasi_chatbot.csv'")


if __name__ == "__main__":
    asyncio.run(main())
