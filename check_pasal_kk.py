import sqlite3
import os

db_path = "vector_store_db_llm_rag/chroma.sqlite3"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Checking Content of Pasal 11 and 12 (Syarat KK) ---")
    # Search for chunks containing "Pasal 11" or "Pasal 12"
    cursor.execute("SELECT c0 FROM embedding_fulltext_search_content WHERE c0 LIKE '%Pasal 11%' OR c0 LIKE '%Pasal 12%'")
    rows = cursor.fetchall()
    
    for i, row in enumerate(rows):
        content = row[0]
        print(f"\nChunk {i+1}:")
        print("-" * 40)
        print(content)
        print("-" * 40)
        
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
