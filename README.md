# AI-Ollama-Hub

This repository provides a Docker Compose setup for the AI-Ollama ecosystem, including services for Ollama, OpenWebUI, Qdrant, and a RAG API.

The goal of this project is to create a completely off-the-grid environment for running and managing AI models, with a focus on RAG (Retrieval-Augmented Generation) capabilities using Ollama.

This stack can be used for various offline applications within our organization, such as:

- MOV.AI platform support
- Internal knowledge bases
- Training and documentation search
- Software development assistance
- Custom AI applications leveraging local models

**Note**: Think of it as a self-hosted alternative to services like ChatGPT, but with an extended knowledge of our code and documentation.

## Services

- **Traefik**: A reverse proxy and load balancer for managing access to the other services.
- **Ollama**: The core service for AI-Ollama.
- **OpenWebUI**: A web-based user interface for interacting with the AI-Ollama services.
- **Qdrant**: A vector search engine for managing and querying embeddings.
- **RAG API**: A Retrieval-Augmented Generation API for advanced querying capabilities.

## Usage

To get started with the AI-Ollama-Hub, follow these steps:

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/ai-ollama-hub.git
   cd ai-ollama-hub
   ```

2. Start the services using Docker Compose:

   ```bash
   docker-compose up -d
   ```

3. Access the services:

   - Traefik Dashboard: http://localhost:8080
   - Ollama: http://ollama.localhost
   - OpenWebUI: http://webui.localhost
   - Qdrant: http://qdrant.localhost
   - RAG API: http://ragapi.localhost

## Models Configuration

Once installed, you need to pull the models you want to use with Ollama. You can do this by running:

```bash
docker exec -it ollama ollama pull <model_name>
```

### Quick Pick Guide

| Needs | Recommended Models (July 2025) |
|-------|-------------------|
| Max CPU efficiency | TinyLlama, GEB-1.3B, SmolLM2, DeepSeek R1 (1.5B) |
| Coding with context | CodeGemma (2–7B), Qwen2.5-Coder (1.5–7B), aiXcoder-7B |
| General performance + CPU | Llama 3 (8B), Mistral 7B, Phi-2 / Phi-3.5-mini |
| Run large models via CPU with quantization | llama.cpp with Q5_K_M GGUF (for 3–7B) |

### Model Pull Commands

- Best overall for CPU code tasks: Qwen2.5-Coder-7B:

```
docker exec -it ollama ollama pull qwen2.5-coder:7b
```


- Ultra-light CPU-friendly models: TinyLlama, GEB-1.3B, SmolLM2

```
docker exec -it ollama ollama pull tinyllama
docker exec -it ollama ollama pull geb:1.3b
docker exec -it ollama ollama pull smollm2:1.7b
```

- Strong and adaptable: Mistral 7B, Llama 3 (8B)

```
docker exec -it ollama ollama pull mistral:7b
docker exec -it ollama ollama pull llama3:8b

```

> **Note**: OpenWebUI doesn’t automatically detect new Ollama models the instant you pull them — it caches the model list when it starts.


### Test Ollama Models

The Ollama service can be tested using the following command which will send a prompt to the model and return the response:

```
curl http://ollama.localhost/api/generate -d '{"model": "llama3:8b-instruct-q4_0", "prompt": "Hello AI"}'
```

### RAG API Usage

RAG stands for Retrieval-Augmented Generation. It allows you to query documents and generate responses based on the retrieved information.

See documentation for the RAG API [here](https://docs.openwebui.com/features/rag).

> **Note**: Ollama doesn’t let you fine-tune in the traditional sense — it’s more about prompt engineering and embedding your knowledge into an external retrieval pipeline.

For example, if we need to inject code into the AI model, we need to use the following approach:

1. Embedding + vector search (your code goes into an index)

2. System prompts (base instructions for context & style)

3.  RAG (feeding relevant code snippets on each query)


#### Extract & Chunk the Code

This step involves breaking down your code into smaller, manageable chunks that can be indexed and searched effectively. You can use tools like `textsplitter` to help with this process.

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pathlib import Path

files = list(Path("/path/to/code").rglob("*.py"))  # add more extensions as needed
texts = []
for file in files:
    content = file.read_text(encoding="utf-8", errors="ignore")
    texts.append({"path": str(file), "content": content})

splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
docs = []
for t in texts:
    for chunk in splitter.split_text(t["content"]):
        docs.append({"path": t["path"], "content": chunk})

```

#### Generate Embeddings and Store in Qdrant

This step is needed to create vector representations of your code chunks, which will be stored in the Qdrant vector database for efficient searching.

```python
   from langchain.embeddings import OpenAIEmbeddings

   embedding_model = OpenAIEmbeddings()
   for doc in docs:
       doc["embedding"] = embedding_model.embed_text(doc["content"])

   # Store embeddings in Qdrant Vector database
   #  running at http://qdrant.localhost

   from langchain.vectorstores import Qdrant
   vector_store = Qdrant()
   vector_store.connect("http://qdrant.localhost")
   vector_store.add_documents(docs)

   vector_store.persist("path/to/store")

```

#### Querying with RAG API

When a user asks something, search for relevant code chunks, then send them along with the question to Qwen2.5 in Ollama:

```python
query = "Explain how this function works"
results = collection.query(query_texts=[query], n_results=5)

context = "\n\n".join(results["documents"][0])
prompt = f"""You are an expert on this codebase.
Context:
{context}
Question: {query}
Answer:"""

import ollama
response = ollama.chat(model="qwen2.5", messages=[{"role": "user", "content": prompt}])
print(response["message"]["content"])
```

### Example

In this example, we will use the `qwen2.5-coder` model to answer questions about the metadata of 2 releases of the MOV.AI platform.

1. First we need to pull the required models, then all actions will be performed offline

```bash
docker exec -it ollama ollama pull nomic-embed-text
docker exec -it ollama ollama pull qwen2.5
```

2. Index the code

We need to create a Python virtual environment, install the required dependencies, and run the indexing script. Make sure to replace `~/work/Training_docs` with the path to your local directory containing the documents you want to index.

The RAG API script will use the `nomic-embed-text` model for generating embeddings and `qwen2.5` for answering questions, taking into account only .py, .yaml/.yml, .json and .md files.

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r rag_api/requirements.txt
python rag_api/release_metadata_rag.py --index --base ~/work/Training_docs
```
