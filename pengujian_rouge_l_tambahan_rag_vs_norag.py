import asyncio
import argparse
import json
import statistics
from datetime import datetime
from pathlib import Path

import httpx
import pandas as pd
from rouge_score import rouge_scorer

from app.services.llm_service import get_llm_model
from app.utils.prompt_templates import evaluation_norag_prompt


BASE_DIR = Path(__file__).resolve().parent
MARKDOWN_PATH = BASE_DIR / "pertanyaan_pengujian_tambahan_rag_vs_tanpa_rag.md"
OUTPUT_PATH = BASE_DIR / "komparasi_rouge_l_tambahan_rag_vs_norag.csv"

BASE_URL = "http://localhost:8000"
ENDPOINT_RAG = f"{BASE_URL}/chat"
ENDPOINT_REGISTER = f"{BASE_URL}/auth/register"
ENDPOINT_LOGIN = f"{BASE_URL}/auth/login"

EVAL_EMAIL = "tester_rouge_l@example.com"
EVAL_PASSWORD = "tester-rouge-l-12345"


def split_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def load_questions_from_markdown(path: Path) -> tuple[list[str], list[str]]:
    if not path.exists():
        raise FileNotFoundError(f"File {path} tidak ditemukan.")

    questions = []
    references = []

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue

        cells = split_markdown_row(line)
        if len(cells) < 3:
            continue

        number, question, reference = cells[:3]
        if not number.isdigit():
            continue
        if not question or not reference:
            continue

        questions.append(question)
        references.append(reference)

    if not questions:
        raise ValueError(f"Tidak ada pertanyaan pengujian yang ditemukan di {path}.")

    return questions, references


async def get_eval_token(client: httpx.AsyncClient) -> str:
    register_payload = {
        "email": EVAL_EMAIL,
        "password": EVAL_PASSWORD,
        "asal_desa": "Evaluasi",
    }
    register_response = await client.post(ENDPOINT_REGISTER, json=register_payload)
    if register_response.status_code not in (200, 400):
        register_response.raise_for_status()

    login_response = await client.post(
        ENDPOINT_LOGIN,
        json={"email": EVAL_EMAIL, "password": EVAL_PASSWORD},
    )
    login_response.raise_for_status()
    return login_response.json()["access_token"]


async def fetch_rag_answer(client: httpx.AsyncClient, question: str, headers: dict[str, str]) -> str:
    try:
        response = await client.post(
            ENDPOINT_RAG,
            json={
                "message": question,
            },
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "Error: Tidak ada response dari server")
    except Exception as exc:
        return f"Error: {exc}"


def extract_answer_from_llm_response(content: str) -> str:
    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed.get("answer", content)
    except json.JSONDecodeError:
        pass
    return content


async def generate_no_rag_answer(llm, question: str) -> str:
    try:
        chain = evaluation_norag_prompt | llm
        response = await chain.ainvoke(
            {
                "question": question,
                "history": "",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        return extract_answer_from_llm_response(response.content)
    except Exception as exc:
        return f"Error: {exc}"


def calculate_rouge_l(
    references: list[str],
    rag_answers: list[str],
    no_rag_answers: list[str],
) -> dict[str, list[float]]:
    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

    rag_precision = []
    rag_recall = []
    rag_f1 = []
    no_rag_precision = []
    no_rag_recall = []
    no_rag_f1 = []

    for reference, rag_answer, no_rag_answer in zip(references, rag_answers, no_rag_answers):
        rag_score = scorer.score(reference, rag_answer)["rougeL"]
        no_rag_score = scorer.score(reference, no_rag_answer)["rougeL"]

        rag_precision.append(rag_score.precision)
        rag_recall.append(rag_score.recall)
        rag_f1.append(rag_score.fmeasure)
        no_rag_precision.append(no_rag_score.precision)
        no_rag_recall.append(no_rag_score.recall)
        no_rag_f1.append(no_rag_score.fmeasure)

    return {
        "rag_precision": rag_precision,
        "rag_recall": rag_recall,
        "rag_f1": rag_f1,
        "no_rag_precision": no_rag_precision,
        "no_rag_recall": no_rag_recall,
        "no_rag_f1": no_rag_f1,
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pengujian ROUGE-L untuk chatbot RAG vs tanpa RAG dari tabel Markdown."
    )
    parser.add_argument(
        "--input",
        default=str(MARKDOWN_PATH),
        help="Path file Markdown berisi tabel Pertanyaan Pengujian dan Jawaban Referensi.",
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_PATH),
        help="Path file CSV output hasil evaluasi ROUGE-L.",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    markdown_path = Path(args.input)
    output_path = Path(args.output)

    print("Membaca pertanyaan pengujian tambahan dari Markdown...")
    questions, references = load_questions_from_markdown(markdown_path)

    rag_answers = []
    no_rag_answers = []

    print(f"\nMulai pengujian ROUGE-L untuk {len(questions)} pertanyaan tambahan.")
    print("Pastikan server FastAPI sedang berjalan di port 8001.\n")

    llm = get_llm_model()

    async with httpx.AsyncClient(timeout=60.0) as client:
        token = await get_eval_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        for index, question in enumerate(questions, start=1):
            print(f"[{index}/{len(questions)}] Memproses pertanyaan: {question}")

            rag_answers.append(await fetch_rag_answer(client, question, headers))
            no_rag_answers.append(await generate_no_rag_answer(llm, question))

    print("\nMenghitung ROUGE-L Precision, Recall, dan F1...")
    rouge = calculate_rouge_l(references, rag_answers, no_rag_answers)

    result_df = pd.DataFrame(
        {
            "Pertanyaan": questions,
            "Referensi": references,
            "Jawaban (Dengan RAG)": rag_answers,
            "Jawaban (Tanpa RAG)": no_rag_answers,
            "RAG - ROUGE-L Precision": rouge["rag_precision"],
            "RAG - ROUGE-L Recall": rouge["rag_recall"],
            "RAG - ROUGE-L F1": rouge["rag_f1"],
            "No-RAG - ROUGE-L Precision": rouge["no_rag_precision"],
            "No-RAG - ROUGE-L Recall": rouge["no_rag_recall"],
            "No-RAG - ROUGE-L F1": rouge["no_rag_f1"],
        }
    )

    result_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print("\n=== HASIL RATA-RATA ROUGE-L PERTANYAAN TAMBAHAN ===")
    print("1. Sistem DENGAN RAG:")
    print(f"   - Precision : {statistics.mean(rouge['rag_precision']):.4f}")
    print(f"   - Recall    : {statistics.mean(rouge['rag_recall']):.4f}")
    print(f"   - F1 Score  : {statistics.mean(rouge['rag_f1']):.4f}")
    print("2. Sistem TANPA RAG:")
    print(f"   - Precision : {statistics.mean(rouge['no_rag_precision']):.4f}")
    print(f"   - Recall    : {statistics.mean(rouge['no_rag_recall']):.4f}")
    print(f"   - F1 Score  : {statistics.mean(rouge['no_rag_f1']):.4f}")
    print(f"\nProses selesai. Hasil disimpan ke '{output_path.name}'.")


if __name__ == "__main__":
    asyncio.run(main())
