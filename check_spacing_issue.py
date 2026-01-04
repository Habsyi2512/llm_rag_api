import sqlite3
import os

db_path = "vector_store_db_llm_rag/chroma.sqlite3"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Checking for Spaced Out Content ---")
    # Get the last 10 chunks added (assuming higher ID is newer)
    cursor.execute("SELECT id, c0 FROM embedding_fulltext_search_content ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    
    for row in rows:
        doc_id = row[0]
        content = row[1]
        print(f"\nID: {doc_id}")
        print("-" * 40)
        # Print first 200 chars
        print(content[:200])
        print("-" * 40)
        
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
