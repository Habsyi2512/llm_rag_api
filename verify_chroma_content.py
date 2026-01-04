import sqlite3
import os

db_path = "vector_store_db_llm_rag/chroma.sqlite3"

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Count total documents
    cursor.execute("SELECT COUNT(*) FROM embedding_fulltext_search_content")
    total_docs = cursor.fetchone()[0]
    print(f"Total documents in vector store: {total_docs}")
    
    # Count Pasal chunks
    cursor.execute("SELECT COUNT(*) FROM embedding_fulltext_search_content WHERE c0 LIKE '%Pasal%'")
    pasal_count = cursor.fetchone()[0]
    print(f"Total chunks containing 'Pasal': {pasal_count}")
    
    # Get samples
    print("\n--- Sample Pasal Chunks ---")
    cursor.execute("SELECT c0 FROM embedding_fulltext_search_content WHERE c0 LIKE '%Pasal%' LIMIT 5")
    rows = cursor.fetchall()
    
    for i, row in enumerate(rows):
        content = row[0]
        print(f"\nChunk {i+1} (Length: {len(content)}):")
        print("-" * 40)
        # Print first 500 chars to avoid flooding
        print(content[:500] + "..." if len(content) > 500 else content)
        print("-" * 40)
        
    conn.close()
    
except Exception as e:
    print(f"Error inspecting database: {e}")
