import os
from fastapi import FastAPI
from qdrant_client import QdrantClient
import requests

app = FastAPI()

OLLAMA_URL_BASE = os.getenv("OLLAMA_URL_BASE", "http://ollama:11434")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant")

print(f"Connecting to Qdrant at: {QDRANT_URL}")
print(f"Connecting to Ollama at: {OLLAMA_URL_BASE}")

qdrant = QdrantClient(url=QDRANT_URL)

COLLECTION = "release_metadata_codebase"
LLM_MODEL = "qwen2.5"



@app.get("/ask")
def ask(q: str):
    # Search in vector DB
    hits = qdrant.search(
        collection_name=COLLECTION,
        query_vector=embed(q),
        limit=3
    )
    context = "\n".join([h.payload['text'] for h in hits])
    prompt = f"Answer using only this context:\n{context}\n\nQuestion: {q}"
    r = requests.post(f"{OLLAMA_URL_BASE}/api/generate", json={"model": LLM_MODEL, "prompt": prompt})
    return r.json()

def embed(text: str):
    # CPU-friendly embedding using Ollama
    r = requests.post(f"{OLLAMA_URL_BASE}/api/embeddings",
                      json={"model": "nomic-embed-text", "input": text})
    return r.json()["embedding"]

# to test the ask endpoint with curl
# curl -X GET "http://rag_api.localhost/ask?q=your_question_here"