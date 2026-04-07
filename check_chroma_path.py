import os
from dotenv import load_dotenv

load_dotenv()

persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./vector_store_db_llm_rag")
abs_path = os.path.abspath(persist_dir)

print(f"Loading Chroma from: {abs_path}")

if os.path.exists(abs_path):
    print("Directory exists.")
    # Check permissions
    import stat
    mode = os.stat(abs_path).st_mode
    print(f"Permissions: {stat.filemode(mode)}")
    
    # List files and their permissions
    for f in os.listdir(abs_path):
        f_path = os.path.join(abs_path, f)
        f_mode = os.stat(f_path).st_mode
        print(f"  {f}: {stat.filemode(f_mode)}")
else:
    print("Directory DOES NOT EXIST.")
