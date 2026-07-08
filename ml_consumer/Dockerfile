# ML consumer: scores raw_comments and writes Neo4j + scored_comments.
# torch 2.12 / transformers 5.x require Python >= 3.11.
FROM python:3.13-slim

WORKDIR /app

# requirements.txt pins CPU-only torch via --extra-index-url (no GPU in compose).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py model_loader.py inference.py database.py ./

# Model weights are NOT baked into the image. Compose bind-mounts
# ./ml_consumer/model_cache to /app/model_cache for reuse across rebuilds.
CMD ["python", "main.py"]
