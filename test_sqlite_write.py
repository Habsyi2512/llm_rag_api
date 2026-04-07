import sqlite3
import os

db_path = "/Users/muhammadhabsyimubarak/Desktop/tugas-akhir/project/llm_rag_gemini_api/vector_store_db_llm_rag/chroma.sqlite3"

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Try to write something
    cur.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)")
    cur.execute("INSERT INTO test DEFAULT VALUES")
    conn.commit()
    print("SUCCESS: Successfully wrote to the database.")
    cur.execute("DROP TABLE test")
    conn.commit()
    conn.close()
except Exception as e:
    print(f"FAILURE: Failed to write to the database: {e}")
