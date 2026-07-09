# Local Setup



Everything runs locally via Docker Compose — no cloud accounts required. This guide takes you from a fresh clone to a fully streaming pipeline with live ML scoring.



## Prerequisites



| Requirement | Notes |

|---|---|

| Docker Desktop | With Docker Compose v2 |

| Python 3.13+ | Only for the one-time dataset fetch and bare-metal development (pandas 3.x requires ≥ 3.11) |

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

docker-compose up --build -d

```



This builds the producer and ML consumer images and starts five containers: `kafka`, `kafka_ui`, `neo4j`, `producer_service`, and `ml_consumer`.



!!! tip "First boot takes a moment"

    Kafka needs ~20 seconds to initialize its KRaft quorum, and Neo4j ~30 seconds for first-time database setup. The first `ml_consumer` **image build** installs PyTorch and transformers (CPU-only torch is pinned to keep this reasonable). The first **container start** downloads toxic-bert weights into `ml_consumer/model_cache/`. Brief connection warnings in early log lines are normal.



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



**Kafka UI:** the `scored_comments` topic exists with a growing message count.



**Neo4j:** graph nodes accumulate as batches commit.



**Fault-tolerance smoke test:**



```bash

docker-compose restart ml_consumer

docker-compose logs -f ml_consumer

```



Processing resumes from the last committed offset — no crash loop.



## Bare-Metal ML Consumer (Optional)



Run the consumer on the host while infrastructure stays in Docker:



```bash

docker-compose up -d kafka neo4j producer_service



cd ml_consumer

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

python main.py

```



Defaults use `localhost:9092` and `bolt://localhost:7687` (host listeners).



## Everyday Operations



| Action | Command |

|---|---|

| Check container status | `docker-compose ps` |

| Tail any service's logs | `docker-compose logs -f <service>` |

| Re-stream the dataset | `docker-compose up -d producer_service` |

| Restart ML consumer | `docker-compose restart ml_consumer` |

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



**Changing the streaming rate.**

Edit `MESSAGES_PER_SECOND` under `producer_service` in `docker-compose.yml` and re-run `docker-compose up -d producer_service`. Bare-metal runs respect the same environment variable.

