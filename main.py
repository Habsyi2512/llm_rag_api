import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": "Bearer 1|GhfAT0STEBRvoVHYGI5Anfc62RKNF7AtXfrrtoXR2067538e"
}

try:
    response = requests.get("http://localhost:8000/api/user", headers=headers)
    response.raise_for_status()
    print("✅ Server responded successfully!")
    print("Response:", response.json())
except requests.exceptions.RequestException as e:
    print(f"❌ Error: {e}")
