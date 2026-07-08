# Local Setup

Everything runs locally via Docker Compose — no cloud accounts required. This guide takes you from a fresh clone to a fully streaming pipeline.

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker Desktop | With Docker Compose v2 |
| Python 3.13+ | Dataset fetch, producer dev, and ML consumer dev (PyTorch + model cache need ~1 GB extra) |
| ~3 GB free disk | Dataset parquet (~400 MB) + PyTorch + Hugging Face model cache + Docker volumes |

## Step 1 — Clone and Fetch the Dataset

The `data/` directory is **gitignored** (it holds ~400 MB of parquet), so it must be generated once after cloning:

```bash
git clone https://github.com/mj-weshh/realtime-moderation-engine.git
cd realtime-moderation-engine/producer_service

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
python fetch_data.py
```

`fetch_data.py` downloads all three `civil_comments` splits and writes four parquet files to the repo-root `data/` folder, including `comments_subset.parquet` — the text-only test split the producer streams from. The script is idempotent; re-running it skips files that already exist.

## Step 2 — Launch the Stack

From the repo root:

```bash
docker-compose up --build -d
```

This builds the producer image and starts four containers: `kafka`, `kafka_ui`, `neo4j`, and `producer_service`.

!!! tip "First boot takes a moment"
    Kafka needs ~20 seconds to initialize its KRaft quorum, and Neo4j ~30 seconds for first-time database setup. The producer's Kafka client retries internally, so brief connection warnings in its first log lines are normal.

## Step 3 — Verify Each Service

### Producer logs

```bash
docker-compose logs -f producer_service
```

Expected output — a startup banner followed by a continuous stream of delivery confirmations:

```text
Streaming 97,320 comments to 'raw_comments' at kafka:29092 (~50 msg/sec)
Message delivered to raw_comments [partition 0]
Message delivered to raw_comments [partition 0]
...
```

### Kafka UI — <http://localhost:8080>

- The `local` cluster shows **Online** with 1 broker.
- Under **Topics**, `raw_comments` exists and its message count climbs at roughly 50/sec.
- Open **Topics → raw_comments → Messages** to inspect live JSON payloads.

### Neo4j Browser — <http://localhost:7474>

- Connect with URL `bolt://localhost:7687`, username `neo4j`, password `testpassword`.
- The database is empty until you run `ml_consumer/database.py` (smoke test) or the Kafka consumer (Day 9). A successful login confirms Neo4j is reachable.

## Step 4 — ML consumer development setup

The ML consumer runs **bare-metal** for now (Docker integration is a later phase). Full module reference: [ML Inference](ml_inference.md).

```powershell
cd ml_consumer
python -m venv venv
.\venv\Scripts\activate        # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
python model_loader.py         # download + cache unitary/toxic-bert (first run only)
python inference.py            # batch scoring smoke test
```

To test Neo4j graph writes, start the database first:

```bash
docker-compose up -d neo4j
cd ml_consumer
python database.py
```

Then open Neo4j Browser and run `MATCH (n) RETURN n LIMIT 25` to see the test node.

## Everyday Operations

| Action | Command |
|---|---|
| Check container status | `docker-compose ps` |
| Tail any service's logs | `docker-compose logs -f <service>` |
| Re-stream the dataset | `docker-compose up -d producer_service` |
| Stop everything | `docker-compose down` |
| Full reset (wipes volumes) | `docker-compose down -v` |
| Rebuild after code changes | `docker-compose up --build -d` |

## Troubleshooting

**The producer container exited with code 0.**
Not an error — the producer is a finite job. It streams the full 97,320-comment dataset (~32 minutes at 50 msg/sec), flushes, and exits cleanly. Restart it to stream again.

**`FileNotFoundError: ... comments_subset.parquet not found`.**
The dataset fetch (Step 1) hasn't been run, so the `./data:/data` mount is empty. Run `fetch_data.py` and restart the producer.

**Kafka UI shows the cluster offline right after startup.**
The UI polls the broker; give KRaft initialization ~20 seconds and refresh.

**Changing the streaming rate.**
Edit `MESSAGES_PER_SECOND` under `producer_service` in `docker-compose.yml` and re-run `docker-compose up -d producer_service`. Bare-metal runs respect the same environment variable.

**`pip install` fails with a TLS / CA bundle error (Windows).**
A stale `CURL_CA_BUNDLE` environment variable may point to a missing PostgreSQL certificate file. Clear it before installing: `$env:CURL_CA_BUNDLE = $null`, then retry `pip install -r requirements.txt`.
