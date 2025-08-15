FROM python:3.11-slim

WORKDIR /app
COPY rag_api.py /app/

RUN pip install --no-cache-dir fastapi uvicorn qdrant-client requests

CMD ["uvicorn", "rag_api:app", "--host", "0.0.0.0", "--port", "8000"]
