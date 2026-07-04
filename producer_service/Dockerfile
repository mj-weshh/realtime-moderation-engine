# Producer service: streams civil_comments into the raw_comments Kafka topic.
# Matches the Python version the requirements were frozen on (pandas 3.x
# and numpy 2.5 require >= 3.11).
FROM python:3.13-slim

WORKDIR /app

# Install dependencies first so this layer is cached across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py fetch_data.py ./

# The dataset is NOT baked into the image (~400MB, gitignored). Compose
# mounts the repo-root ./data folder to /data, where main.py's path
# resolution (parents[1] of /app/main.py) expects it.
CMD ["python", "main.py"]
