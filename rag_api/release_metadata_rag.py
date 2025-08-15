#!/usr/bin/env python3
import argparse
import os
from pathlib import Path
import ollama
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance, Filter, FieldCondition, MatchValue
from chromadb.utils import embedding_functions  # only using Ollama embedding wrapper

# Config
QDRANT_URL = "http://qdrant.localhost"
COLLECTION_NAME = "release_metadata_codebase"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen2.5"

# ----------- File collection & classification -----------

def detect_type_from_path_or_content(filepath, content):
    path_str = str(filepath).lower()
    if "annotations" in path_str:
        return "annotations"
    elif "flows" in path_str:
        return "flows"
    elif "nodes" in path_str:
        return "nodes"
    elif "callbacks" in path_str:
        return "callbacks"
    else:
        return "other"

def collect_files(base_dir):
    exts = {".py", ".yaml", ".yml", ".json"}
    files = []
    for root, _, filenames in os.walk(base_dir):
        for fn in filenames:
            if Path(fn).suffix.lower() in exts:
                files.append(Path(root) / fn)
    return files

def read_file_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception:
        return ""

def simple_chunk_with_line_numbers(text, chunk_size=512, overlap=50):
    lines = text.split("\n")
    chunks = []
    i = 0
    while i < len(lines):
        chunk_lines = lines[i:i+chunk_size]
        chunk_text = "\n".join(chunk_lines)
        chunks.append((chunk_text, i+1))  # start line is 1-based
        i += chunk_size - overlap
    return chunks

# ----------- Qdrant helpers -----------

def get_qdrant_client():
    return QdrantClient(url=QDRANT_URL)

def ensure_collection(client: QdrantClient, vector_size: int):
    # Always rebuild for this project
    try:
        client.delete_collection(COLLECTION_NAME)
    except:
        pass
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
    )

def embed_texts(texts):
    ef = embedding_functions.OllamaEmbeddingFunction(model_name=EMBED_MODEL)
    return [ef(text) for text in texts]

# ----------- Indexing -----------

def index_code_qdrant(base_dir):
    client = get_qdrant_client()
    ef = embedding_functions.OllamaEmbeddingFunction(model_name=EMBED_MODEL)

    files = collect_files(base_dir)
    print(f"[INFO] Found {len(files)} files.")

    all_chunks = []
    for file in files:
        text = read_file_text(file)
        if not text.strip():
            continue
        chunks = simple_chunk_with_line_numbers(text)
        ftype = detect_type_from_path_or_content(file, text)
        for chunk_text, start_line in chunks:
            all_chunks.append({
                "text": chunk_text,
                "metadata": {
                    "path": str(file),
                    "start_line": start_line,
                    "type": ftype,
                    "ext": file.suffix.lower()
                }
            })

    ensure_collection(client, vector_size=len(ef("test")))

    batch_size = 64
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i:i+batch_size]
        ids = [abs(hash(b["path"] + str(b["start_line"]))) % (2**63) for b in batch]
        vectors = [ef(b["text"]) for b in batch]
        payloads = [{**b["metadata"], "text": b["text"]} for b in batch]
        client.upsert(collection_name=COLLECTION_NAME, points=zip(ids, vectors, payloads))

    print(f"[INFO] Indexed {len(all_chunks)} chunks into Qdrant.")

# ----------- Query -----------

def build_prompt_with_context(question, chunks):
    context_str = ""
    for ch in chunks:
        meta = ch["metadata"]
        context_str += f"\n### File: {meta['path']} (line {meta['start_line']})\n{ch['document']}\n"
    return f"Answer the question using the following code context:\n{context_str}\n\nQuestion: {question}\nAnswer:"

def query_code_qdrant(question, n_results=5, filter_type=None, filename_filter=None):
    client = get_qdrant_client()
    ef = embedding_functions.OllamaEmbeddingFunction(model_name=EMBED_MODEL)
    query_vector = ef(question)

    filters = []
    if filter_type and filter_type.lower() != "all":
        filters.append(FieldCondition(key="type", match=MatchValue(value=filter_type)))
    if filename_filter:
        filters.append(FieldCondition(key="path", match=MatchValue(value=filename_filter)))

    qdrant_filter = Filter(must=filters) if filters else None

    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=n_results,
        query_filter=qdrant_filter,
        with_payload=True
    )

    chunks = []
    for r in results:
        payload = r.payload
        chunks.append({
            "document": payload.get("text", ""),
            "metadata": {
                "path": payload.get("path"),
                "start_line": payload.get("start_line"),
                "type": payload.get("type"),
                "ext": payload.get("ext")
            }
        })

    prompt = build_prompt_with_context(question, chunks)
    resp = ollama.chat(model=LLM_MODEL, messages=[{"role": "user", "content": prompt}])
    return resp["message"]["content"], chunks

# ----------- CLI -----------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", action="store_true", help="Index the codebase into Qdrant")
    parser.add_argument("--ask", type=str, help="Ask a question to the LLM")
    parser.add_argument("--base", type=str, help="Base directory of the code")
    parser.add_argument("--filter-type", type=str, default="all", help="Filter by type: annotations, flows, nodes, callbacks, other, all")
    parser.add_argument("--filename", type=str, help="Filter by exact filename")
    args = parser.parse_args()

    if args.index:
        if not args.base:
            print("Error: --base is required for indexing")
        else:
            index_code_qdrant(args.base)

    if args.ask:
        answer, ctx = query_code_qdrant(args.ask, filter_type=args.filter_type, filename_filter=args.filename)
        print("\n=== Answer ===\n", answer)
        print("\n=== Context Used ===")
        for c in ctx:
            print(f"{c['metadata']['path']} (line {c['metadata']['start_line']})")
