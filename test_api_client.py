"""
Script sederhana untuk menguji fungsi-fungsi di api_client.py secara terisolasi.
Pastikan:
1. File .env berada di direktori yang sama dengan script ini (llm_rag_gemini_api/).
2. Variabel LARAVEL_API_BASE_URL dan LARAVEL_API_TOKEN di .env sudah benar.
3. Aplikasi Laravel Anda sedang berjalan di URL yang ditentukan di .env.
"""

import asyncio
import sys
import os
import httpx
import logging

# Atur logging ke level INFO atau DEBUG untuk melihat detail
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Tambahkan direktori root proyek ke sys.path agar Python bisa menemukan modul 'app'
sys.path.insert(0, os.path.abspath('.'))

from app.core.config import settings

# Headers
headers = {
    "Authorization": f"Bearer {settings.LARAVEL_API_TOKEN}",
    "Accept" : "application/json"
}

async def test_fetch_faqs():
    print("--- Testing Fetch FAQs ---")
    url = f"{settings.LARAVEL_API_BASE_URL}/faqs" # Gunakan path yang benar berdasarkan LARAVEL_API_BASE_URL
    timeout = httpx.Timeout(settings.LARAVEL_API_TIMEOUT)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            print(f"Fetching FAQs from {url} with headers: {headers}")
            response = await client.get(url, headers=headers)
            print(f"Status Code: {response.status_code}")
            print(f"Response Text (first 200 chars): {response.text[:200]}")
            print(f"Response Headers: {dict(response.headers)}")

            response.raise_for_status() # Akan melempar HTTPStatusError jika status bukan 2xx
            print("Attempting to parse JSON...")
            try:
                data = response.json() # Baris yang menyebabkan error
                print(f"Parsed JSON data: {data}")

                # Asumsi API mengembalikan data dalam format { "data": [...] } atau langsung array [...]
                faqs_raw = data.get('data', data)

                # Validasi apakah faqs_raw adalah list
                if not isinstance(faqs_raw, list):
                    print(f"ERROR: Expected 'faqs' data to be a list, got {type(faqs_raw)}. Data: {faqs_raw}")
                    return [] # Kembalikan list kosong jika bukan list

                processed_faqs = []
                for item in faqs_raw:
                    # Validasi apakah item adalah dict
                    if not isinstance(item, dict):
                        print(f"WARNING: Skipping non-dict item in faqs: {item}")
                        continue
                    # Gabungkan question dan answer sebagai satu dokumen
                    content = f"Pertanyaan: {item.get('question', '')}\nJawaban: {item.get('answer', '')}"
                    processed_faqs.append({
                        "page_content": content,
                        "metadata" : {
                            "source": "faq",
                            "id" : item.get('id', '')
                        }
                    })
                print(f"Success: Fetched and processed {len(processed_faqs)} FAQs.")
                # Cetak beberapa FAQ sebagai contoh
                for i, faq in enumerate(processed_faqs[:2]): # Hanya cetak 2 pertama
                    print(f"  FAQ {i+1}:")
                    print(f"    Content: {faq.get('page_content', '')[:100]}...") # Ambil 100 karakter pertama
                    print(f"    Meta {faq.get('metadata', {})}")
            except ValueError as e:
                print(f"FAILED: Could not parse JSON. Error: {e}")
                print(f"Raw response text was: '{response.text}'")
                return []
        print("--- End Testing Fetch FAQs ---\n")

    except httpx.HTTPStatusError as e:
        print(f"FAILED: HTTP error fetching FAQs: {e}. Response: {e.response.text if e.response else 'No response body'}")
    except httpx.RequestError as e:
        print(f"FAILED: Request error fetching FAQs: {e}")
    except Exception as e:
        print(f"FAILED: Unexpected error during FAQ fetch test: {e}")


async def test_fetch_documents():
    print("--- Testing Fetch Documents ---")
    url = f"{settings.LARAVEL_API_BASE_URL}/documents" # Gunakan path yang benar
    timeout = httpx.Timeout(settings.LARAVEL_API_TIMEOUT)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            print(f"Fetching Documents from {url} with headers: {headers}")
            response = await client.get(url, headers=headers)
            print(f"Status Code: {response.status_code}")
            print(f"Response Text (first 200 chars): {response.text[:200]}")
            print(f"Response Headers: {dict(response.headers)}")

            response.raise_for_status()
            print("Attempting to parse JSON...")
            try:
                data = response.json() # Baris yang menyebabkan error
                print(f"Parsed JSON data: {data}")

                # Asumsi API mengembalikan data dalam format { "data": [...] } atau langsung array [...]
                docs_raw = data.get('data', data)

                # Validasi apakah docs_raw adalah list
                if not isinstance(docs_raw, list):
                    print(f"ERROR: Expected 'documents' data to be a list, got {type(docs_raw)}. Data: {docs_raw}")
                    return []

                processed_docs = []
                for item in docs_raw:
                    # Validasi apakah item adalah dict
                    if not isinstance(item, dict):
                        print(f"WARNING: Skipping non-dict item in documents: {item}")
                        continue
                    # Asumsi item memiliki 'content' dan 'id'
                    content = item.get('content', '')
                    if content: # Pastikan konten tidak kosong
                        processed_docs.append({
                            "page_content": content,
                            "metadata": {"source": "document", "id": item.get('id')}
                        })
                print(f"Success: Fetched and processed {len(processed_docs)} Documents.")
                # Cetak beberapa Dokumen sebagai contoh
                for i, doc in enumerate(processed_docs[:2]): # Hanya cetak 2 pertama
                    print(f"  Doc {i+1}:")
                    print(f"    Content (first 100 chars): {doc.get('page_content', '')[:100]}...")
                    print(f"    Meta {doc.get('metadata', {})}")
            except ValueError as e:
                print(f"FAILED: Could not parse JSON. Error: {e}")
                print(f"Raw response text was: '{response.text}'")
                return []
        print("--- End Testing Fetch Documents ---\n")

    except httpx.HTTPStatusError as e:
        print(f"FAILED: HTTP error fetching Documents: {e}. Response: {e.response.text if e.response else 'No response body'}")
    except httpx.RequestError as e:
        print(f"FAILED: Request error fetching Documents: {e}")
    except Exception as e:
        print(f"FAILED: Unexpected error during Document fetch test: {e}")


async def main():
    print("Starting API Client Tests...\n")
    await test_fetch_faqs()
    await test_fetch_documents()
    print("API Client Tests Completed.")

if __name__ == "__main__":
    # asyncio.run() digunakan untuk menjalankan fungsi async utama
    asyncio.run(main())