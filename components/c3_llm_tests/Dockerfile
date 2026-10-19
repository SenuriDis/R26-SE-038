FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
# CPU-only PyTorch for the HuggingFace embeddings: the default Linux wheel
# pulls several GB of CUDA libraries this container never uses.
RUN pip install --no-cache-dir --default-timeout=300 --retries 10 \
        torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir --default-timeout=300 --retries 10 -r requirements.txt

COPY . .

ENV API_HOST=0.0.0.0
ENV API_PORT=8003

EXPOSE 8003

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8003"]
