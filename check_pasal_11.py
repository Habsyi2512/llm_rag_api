import sqlite3
import os

db_path = "vector_store_db_llm_rag/chroma.sqlite3"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Checking Content of Pasal 11 (Specific) ---")
    # Try to find Pasal 11 specifically, maybe it was missed or split weirdly
    cursor.execute("SELECT c0 FROM embedding_fulltext_search_content WHERE c0 LIKE '%Pasal 11%'")
    rows = cursor.fetchall()
    
    if not rows:
        print("Pasal 11 NOT FOUND in exact match.")
        # Try broader search
        cursor.execute("SELECT c0 FROM embedding_fulltext_search_content WHERE c0 LIKE '%Penerbitan KK baru%'")
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
