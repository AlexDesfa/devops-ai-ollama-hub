from fastapi import FastAPI
from qdrant_client import QdrantClient
import requests

app = FastAPI()
qdrant = QdrantClient("localhost", port=6333)

OLLAMA_URL = "http://localhost:11434/api/generate"
COLLECTION = "lab_docs"

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
    r = requests.post(OLLAMA_URL, json={"model": "llama3:8b-instruct-q4_0", "prompt": prompt})
    return r.json()

def embed(text: str):
    # CPU-friendly embedding using Ollama
    r = requests.post("http://localhost:11434/api/embeddings",
                      json={"model": "nomic-embed-text", "input": text})
    return r.json()["embedding"]