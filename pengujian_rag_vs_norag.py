import pandas as pd
import httpx
import asyncio
from bert_score import score
from rouge_score import rouge_scorer
from app.core.config import settings

# Path ke file CSV yang berisi Ground Truth
CSV_PATH = "hasil_evaluasi_chatbot.csv"

# Konfigurasi Endpoints Endpoint API
BASE_URL = "http://localhost:8001"
ENDPOINT_RAG = f"{BASE_URL}/chat"
ENDPOINT_NO_RAG = f"{BASE_URL}/chat/no-rag"

API_KEY = settings.FASTAPI_API_KEY
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

async def fetch_answer(client: httpx.AsyncClient, url: str, question: str) -> str:
    try:
        response = await client.post(url, json={"message": question, "user_id": "tester", "is_eval": True}, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "Error: Tidak ada response dari server")
    except Exception as e:
        return f"Error: {str(e)}"

async def main():
    print("Membaca file dataset ground truth...")
    try:
        df = pd.read_csv(CSV_PATH)
    except FileNotFoundError:
        print(f"File {CSV_PATH} tidak ditemukan.")
        return

    # Ambil semua pertanyaan
    pertanyaan_list = df["Pertanyaan"].tolist()
    referensi_list = df["Referensi"].tolist()

    jawaban_rag = []
    jawaban_no_rag = []

    print(f"\nMulai melakukan pengujian untuk {len(pertanyaan_list)} pertanyaan...")
    print("Pastikan server FastAPI Anda sedang berjalan di port 8001.\n")

    # Ambil jawaban dari API
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, q in enumerate(pertanyaan_list, start=1):
            print(f"[{i}/{len(pertanyaan_list)}] Memproses pertanyaan: {q}")
            
            # Hit RAG
            ans_rag = await fetch_answer(client, ENDPOINT_RAG, q)
            jawaban_rag.append(ans_rag)
            
            # Hit No-RAG
            ans_no_rag = await fetch_answer(client, ENDPOINT_NO_RAG, q)
            jawaban_no_rag.append(ans_no_rag)

    print("\nMenghitung metrik BERTScore secara Semantik...")
    P_rag, R_rag, F1_rag = score(jawaban_rag, referensi_list, lang="id", model_type="xlm-roberta-base")
    P_norag, R_norag, F1_norag = score(jawaban_no_rag, referensi_list, lang="id", model_type="xlm-roberta-base")

    print("Menghitung metrik ROUGE secara Leksikal (Exact String Match)...")
    scorer_rouge = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    
    rougeL_f1_rag = []
    rougeL_f1_norag = []
    
    for ref, ans_r, ans_nr in zip(referensi_list, jawaban_rag, jawaban_no_rag):
        score_rag = scorer_rouge.score(ref, ans_r)
        rougeL_f1_rag.append(score_rag['rougeL'].fmeasure)
        
        score_nr = scorer_rouge.score(ref, ans_nr)
        rougeL_f1_norag.append(score_nr['rougeL'].fmeasure)

    # DataFrame Synthesis
    hasil_df = pd.DataFrame({
        "Pertanyaan": pertanyaan_list,
        "Referensi": referensi_list,
        "Jawaban (Dengan RAG)": jawaban_rag,
        "Jawaban (Tanpa RAG)": jawaban_no_rag,
        
        # BERTScore
        "RAG - BERT(F1)": [f.item() for f in F1_rag],
        "No-RAG - BERT(F1)": [f.item() for f in F1_norag],
        
        # ROUGE Score
        "RAG - ROUGE-L F1": rougeL_f1_rag,
        "No-RAG - ROUGE-L F1": rougeL_f1_norag,
    })

    print("\n=== HASIL RATA-RATA EVALUASI ===")
    
    print("\n[METRIK BERTSCORE (Semantic - Kebal Halusinasi)]")
    print("1. Sistem DENGAN RAG:")
    print(f"   - F1 Score  : {F1_rag.mean().item():.4f}")
    print("2. Sistem TANPA RAG:")
    print(f"   - F1 Score  : {F1_norag.mean().item():.4f}")
    
    print("\n[METRIK ROUGE-L (Lexical Exact Match - Sensitif Halusinasi)]")
    import statistics
    print("1. Sistem DENGAN RAG:")
    print(f"   - F1 Score  : {statistics.mean(rougeL_f1_rag):.4f}")
    print("2. Sistem TANPA RAG:")
    print(f"   - F1 Score  : {statistics.mean(rougeL_f1_norag):.4f}")

    # Simpan ke CSV baru
    output_filename = "komparasi_rag_vs_norag.csv"
    hasil_df.to_csv(output_filename, index=False, encoding="utf-8-sig")
    print(f"\n✅ Proses selesai! Laporan lengkap hasil komparasi telah disimpan ke file '{output_filename}'")

if __name__ == "__main__":
    import os
    from bert_score import model2layers
    # Setting aman untuk bert score indonesia di laptop lokal
    model2layers["xlm-roberta-base"] = 12
    asyncio.run(main())
