#!/usr/bin/env python3
"""
Local RAG with Qdrant + Ollama
Indexes Python, YAML, JSON files into Qdrant with metadata.
Queries Qwen2.5 through Ollama using retrieved context.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional

from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue
import ollama


# -----------------------
# Configuration
# -----------------------

COLLECTION_NAME = "release_metadata_codebase"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen2.5"

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama.localhost")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant.localhost")

print(f"Connecting to Qdrant at: {QDRANT_URL}")
print(f"Connecting to Ollama at: {OLLAMA_HOST}")

client_qdrant = QdrantClient(url=QDRANT_URL, port=80)
# test qdrant connection
try:
    client_qdrant.info()
    print("[INFO] Successfully connected to Qdrant.")
except Exception as e:
    print(f"[ERROR] Could not connect to Qdrant: {e}")
    exit(1)

client_ollama = ollama.Client(host=OLLAMA_HOST)
# test ollama connection
try:
    client_ollama.list()
    print("[INFO] Successfully connected to Ollama.")
except Exception as e:
    print(f"[ERROR] Could not connect to Ollama: {e}")


# -----------------------
# Helpers
# -----------------------

def classify_file(path: Path) -> str:
    """Classify file type based on path name."""
    p = str(path).lower()
    if "annotations" in p:
        return "annotations"
    elif "flows" in p:
        return "flows"
    elif "nodes" in p:
        return "nodes"
    elif "callbacks" in p:
        return "callbacks"
    else:
        return "other"


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks."""
    lines = text.splitlines()
    chunks = []
    start = 0
    while start < len(lines):
        end = min(start + chunk_size, len(lines))
        chunk = "\n".join(lines[start:end])
        chunks.append((chunk, start + 1))  # store start line (1-based)
        if end == len(lines):
            break
        start = end - overlap
    return chunks


def embed_text(text: str) -> List[float]:
    """Get embedding from Ollama for a single string."""
    resp = client_ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return resp["embedding"]


# -----------------------
# Indexing
# -----------------------

def index_codebase(source_dir: Path):
    """Rebuild Qdrant collection from source directory."""
    print(f"[INFO] Rebuilding collection '{COLLECTION_NAME}' in Qdrant at {QDRANT_URL}")

    # Delete existing collection if exists
    try:
        client_qdrant.delete_collection(collection_name=COLLECTION_NAME)
    except Exception:
        pass

    # Create new collection
    client_qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
    )

    points = []
    point_id = 1

    files = list(source_dir.rglob("*.[pj][sy][mo]*"))  # match .py, .yaml/.yml, .json, .md
    for file_path in tqdm(files, desc="Indexing files"):
        if file_path.suffix.lower() not in [".py", ".yaml", ".yml", ".json", ".md"]:
            continue

        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            print(f"[WARN] Could not read {file_path}: {e}")
            continue

        file_type = classify_file(file_path)
        chunks = chunk_text(text, chunk_size=40, overlap=5)

        for chunk, start_line in chunks:
            emb = embed_text(chunk)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=emb,
                    payload={
                        "type": file_type,
                        "path": str(file_path),
                        "ext": file_path.suffix.lower(),
                        "start_line": start_line,
                        "content": chunk
                    }
                )
            )
            point_id += 1

    if points:
        client_qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"[INFO] Indexed {len(points)} chunks.")


# -----------------------
# Querying
# -----------------------


def query_codebase(query: str, filters: Optional[Dict] = None, top_k: int = 5) -> str:
    """Query Qdrant and pass retrieved context to Qwen."""
    emb = embed_text(query)

    must_conditions = []
    if filters:
        for key, value in filters.items():
            must_conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))

    qdrant_filter = Filter(must=must_conditions) if must_conditions else None

    search_result = client_qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=emb,
        limit=top_k,
        query_filter=qdrant_filter
    )

    context_parts = []
    for r in search_result:
        meta = r.payload
        if meta:
            context_parts.append(
                f"File: {meta['path']} (start line {meta['start_line']})\n{meta['content']}"
            )

    context_text = "\n\n---\n\n".join(context_parts)
    prompt = f"Using the following code context:\n{context_text}\n\nAnswer the question:\n{query}"

    resp = client_ollama.chat(model=LLM_MODEL, messages=[
        {"role": "user", "content": prompt}
    ])
    return resp["message"]["content"]


# -----------------------
# CLI
# -----------------------

def main():
    parser = argparse.ArgumentParser(description="Local RAG with Qdrant + Ollama")
    parser.add_argument("--index", type=str, help="Path to codebase to index")
    parser.add_argument("--query", type=str, help="Query to run")
    parser.add_argument("--filter-type", type=str, help="Filter by file type")
    parser.add_argument("--filter-ext", type=str, help="Filter by file extension (.py, .yaml, .json, .md)")
    args = parser.parse_args()

    if args.index:
        index_codebase(Path(args.index))

    if args.query:
        filters = {}
        if args.filter_type:
            filters["type"] = args.filter_type
        if args.filter_ext:
            filters["ext"] = args.filter_ext.lower()
        answer = query_codebase(args.query, filters=filters)
        print("\n[ANSWER]\n", answer)


if __name__ == "__main__":
    main()
