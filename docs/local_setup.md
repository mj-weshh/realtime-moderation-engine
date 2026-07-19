# Local Setup

Everything runs locally via Docker Compose — no cloud accounts required. This guide takes you from a fresh clone to a fully streaming pipeline with ML scoring and WebSocket alerts.

## Prerequisites

| Requirement | Notes |
|---|---|
| Docker Desktop | With Docker Compose v2 |
| Python 3.13+ | Only for the one-time dataset fetch (pandas 3.x requires ≥ 3.11) |
| ~2 GB free disk | Dataset parquet files (~400 MB) + Hugging Face model cache + Docker volumes |

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
docker-compose down -v
docker-compose up --build -d
```

This builds the producer, ML consumer, WebSocket API, and Next.js dashboard images and starts seven containers: `kafka`, `kafka_ui`, `neo4j`, `producer_service`, `ml_consumer`, `websocket_api`, and `nextjs_client`.

!!! tip "First boot takes a moment"
    Kafka needs ~20 seconds to initialize its KRaft quorum, and Neo4j ~30 seconds for first-time database setup. The first `ml_consumer` **image build** installs PyTorch and transformers (CPU-only torch is pinned to keep this reasonable). The first **container start** downloads toxic-bert weights into `ml_consumer/model_cache/`. The `websocket_api` image installs Node dependencies on first build. The `nextjs_client` image runs a production Next.js compile (~1–2 minutes first time). Brief connection warnings in early log lines are normal.

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
- The `scored_comments` topic grows as the ML consumer processes batches.
- Open **Topics → raw_comments → Messages** to inspect live JSON payloads.

### Neo4j Browser — <http://localhost:7474>

- Connect with URL `bolt://localhost:7687`, username `neo4j`, password `testpassword`.
- Run `MATCH (n) RETURN n LIMIT 25` — once the ML consumer is processing, User and Comment nodes with `POSTED` and `REPLIES_TO` edges appear.

## Step 4 — Verify ML Consumer

```bash
docker-compose logs -f ml_consumer
```

Expected output after model warm-up:

```text
ML consumer starting: raw_comments -> scored_comments at kafka:29092 (batch=16, group=ml_consumer_group)
Model loaded.
Processed batch of 16 message(s)
Processed batch of 16 message(s)
...
```

**Fault-tolerance smoke test:**

```bash
docker-compose restart ml_consumer
docker-compose logs -f ml_consumer
```

Processing resumes from the last committed offset — no crash loop.

## Step 5 — Verify WebSocket API

```bash
docker-compose logs -f websocket_api
```

Expected output:

```text
HTTP and WebSocket server listening on port 8081
Connected to Kafka; listening on scored_comments ...
WebSocket client connected
```

**Health check:**

```bash
curl http://localhost:8081/health
```

Returns `{"status":"ok"}`.

**WebSocket client:**

```bash
npx wscat -c ws://localhost:8081
```

You should receive JSON payloads only when `is_flagged: true` and `scores.toxicity >= 0.5`. Benign comments are filtered at the bridge.

## Step 6 — Verify Dashboard

Open <http://localhost:3000> in a browser.

- The **Live Alert Feed** (left column) shows scrolling flagged comments with toxicity color-coding.
- The **Network Graph** (right column) renders an animating force-directed graph of users and comments.
- Both panels update in real time as the pipeline streams.

```bash
docker-compose logs -f nextjs_client
```

If the feed shows "Connecting to alert stream…" for more than a few seconds, confirm `websocket_api` is running and the ML consumer is producing flagged messages (see troubleshooting below).

### Full E2E checklist

| Step | Command / URL | Success |
|---|---|---|
| Producer streaming | `docker-compose logs producer_service` | Delivery confirmations to `raw_comments` |
| ML scoring | `docker-compose logs ml_consumer` | `Processed batch of N message(s)` |
| Kafka topics | http://localhost:8080 | Both topics growing |
| Neo4j graph | http://localhost:7474 | User/Comment nodes present |
| WebSocket health | `curl http://localhost:8081/health` | `{"status":"ok"}` |
| Flagged alerts | `npx wscat -c ws://localhost:8081` | Flagged JSON only |
| Dashboard | http://localhost:3000 | Live feed + force graph updating |

## Bare-Metal Development (Optional)

**ML consumer** on the host while infrastructure stays in Docker:

```bash
docker-compose up -d kafka neo4j producer_service

cd ml_consumer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

**WebSocket API** on the host:

```bash
docker-compose up -d kafka producer_service ml_consumer

cd backend_api
npm install
node index.js
```

Defaults use `localhost:9092` for Kafka and listen on `:8081`.

**Frontend dashboard** on the host (infrastructure in Docker):

```bash
docker-compose up -d kafka producer_service ml_consumer websocket_api

cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. WebSocket defaults to `ws://localhost:8081`. See [Frontend Dashboard](frontend.md) for component details.

## Everyday Operations

| Action | Command |
|---|---|
| Check container status | `docker-compose ps` |
| Tail any service's logs | `docker-compose logs -f <service>` |
| Re-stream the dataset | `docker-compose up -d producer_service` |
| Restart ML consumer | `docker-compose restart ml_consumer` |
| Restart WebSocket API | `docker-compose restart websocket_api` |
| Restart dashboard | `docker-compose restart nextjs_client` |
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

**The first `ml_consumer` build is very slow.**
PyTorch and transformers are large dependencies. CPU-only PyTorch (pinned in `requirements.txt`) avoids the ~526 MB CUDA wheel. Allow several minutes on first build; later rebuilds use Docker layer cache.

**Model weights re-download on every start.**
They should persist in `./ml_consumer/model_cache/` via the compose bind mount. If the directory is missing or wiped, the first start re-fetches from Hugging Face.

**No WebSocket messages in wscat.**
Ensure `ml_consumer` is running and processing (`scored_comments` growing in Kafka UI). Connect wscat before or during an active stream — the bridge uses `fromBeginning: false`, so it only forwards messages arriving after connect. Most traffic is benign and filtered; flagged messages are a subset of the stream.

**`websocket_api` cannot connect to Kafka.**
Confirm the stack is up (`docker-compose ps`) and Kafka has finished KRaft init. Inside the container, the broker is `kafka:29092`, not `localhost:9092`.

**Changing the streaming rate.**
Edit `MESSAGES_PER_SECOND` under `producer_service` in `docker-compose.yml` and re-run `docker-compose up -d producer_service`. Bare-metal runs respect the same environment variable.

**Dashboard shows "Connecting to alert stream…" indefinitely.**
Confirm `websocket_api` is healthy (`curl http://localhost:8081/health`) and `ml_consumer` is processing batches. The dashboard WebSocket targets `ws://localhost:8081` from the browser — ensure that port is reachable. Most stream traffic is benign and filtered; wait for flagged messages to appear.
