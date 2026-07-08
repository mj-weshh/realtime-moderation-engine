# Real-Time Moderation Engine

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Apache Kafka](https://img.shields.io/badge/Apache%20Kafka-KRaft-231F20?logo=apachekafka&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-5%20Community-4581C3?logo=neo4j&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C?logo=pytorch&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

A high-throughput, distributed data pipeline that ingests simulated social media traffic, scores it for **toxicity and misinformation in real time**, maps malicious network clusters in a graph database, and (in upcoming phases) streams flagged alerts to a live command-center dashboard.

The project demonstrates production-grade MLOps, event-driven microservice architecture, and strict SOLID engineering — built as a fully local, Dockerized system.

## How It Works

The [`google/civil_comments`](https://huggingface.co/datasets/google/civil_comments) dataset (~97k test-split comments) is enriched with a synthetic social graph — user identities and reply chains — and streamed into Apache Kafka at a configurable rate. The **ml_consumer** scores each comment with a transformer model and writes the conversation graph to Neo4j; the WebSocket API and Next.js dashboard (Week 2–3) will surface flagged events live.

## Current Architecture

> **Status:** Week 2 in progress — the containerized producer is live; **ml_consumer core logic** (model loading, batched inference, Neo4j graph writes) is implemented as standalone modules. Kafka orchestration and Docker integration for the consumer are next.

The stack runs Kafka in **KRaft mode** (no Zookeeper). All containerized services share `moderation_network` and address each other by service name. The ML consumer currently runs bare-metal for development.

```mermaid
flowchart LR
    subgraph hostMachine [Host Machine]
        dataset[("data/ parquet")]
        mlConsumer[ml_consumer<br/>bare-metal dev]
        browser[Browser]
    end

    subgraph modNet [moderation_network - Docker bridge]
        producer[producer_service]
        kafka[(Kafka KRaft)]
        kafkaui[Kafka UI]
        neo4j[(Neo4j 5)]
    end

    dataset -- "read-only mount" --> producer
    producer -- "raw_comments" --> kafka
    kafka -. "Day 9: consume" .-> mlConsumer
    mlConsumer -. "score + graph write" .-> neo4j
    mlConsumer -. "Day 9: scored_comments" .-> kafka
    kafka --> kafkaui
    browser -- ":8080" --> kafkaui
    browser -- ":7474" --> neo4j
```

| Service | Image / Runtime | Purpose | Host Ports |
|---|---|---|---|
| `kafka` | `confluentinc/cp-kafka` (KRaft) | Event streaming backbone | `9092` |
| `kafka_ui` | `provectuslabs/kafka-ui` | Visual topic/consumer inspection | `8080` |
| `neo4j` | `neo4j:5-community` | Graph storage for user/comment networks | `7474`, `7687` |
| `producer_service` | Python 3.13 (custom image) | Streams enriched comments into Kafka | — |
| `ml_consumer` | Python 3.13 (bare-metal) | Toxicity inference + Neo4j graph writes | — |

## Prerequisites

- **Docker Desktop** with Docker Compose
- **Python 3.13+** (dataset fetch, producer dev, and ML consumer dev)
- **~3 GB free disk** for dataset parquet, PyTorch, and model cache

## Quick Start

```bash
# 1. Clone and enter the repo
git clone https://github.com/mj-weshh/realtime-moderation-engine.git
cd realtime-moderation-engine

# 2. One-time dataset fetch (the data/ folder is gitignored)
cd producer_service
python -m venv venv
venv\Scripts\activate        # Windows  |  source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
python fetch_data.py
cd ..

# 3. Build and launch the stack
docker-compose up --build -d

# 4. Watch the producer stream
docker-compose logs -f producer_service
```

**Verify it's alive:**

- Kafka UI — <http://localhost:8080> → the `raw_comments` topic message count climbs at ~50 msg/sec.
- Neo4j Browser — <http://localhost:7474> (login `neo4j` / `testpassword`).

The producer streams the full 97k-comment dataset (~32 minutes at the default rate) and exits cleanly. Re-run it with `docker-compose up -d producer_service`.

For ML consumer setup (model download, inference, Neo4j smoke tests), see [docs/ml_inference.md](docs/ml_inference.md) or the MkDocs site.

## Documentation

Full documentation is built with MkDocs Material:

```bash
pip install mkdocs mkdocs-material
mkdocs serve
```

Then open <http://127.0.0.1:8000>.

## Project Structure

```
realtime-moderation-engine/
├── producer_service/    # Streams enriched comments to Kafka (containerized)
├── ml_consumer/       # Model loader, inference, Neo4j graph writer (bare-metal)
│   ├── model_loader.py
│   ├── inference.py
│   └── database.py
├── backend_api/         # (Week 2) Kafka -> WebSocket bridge
├── frontend/            # (Week 3) Next.js real-time dashboard
├── docs/                # MkDocs pages, PRD, implementation plan
└── docker-compose.yml   # Single-command orchestration
```

## License

MIT — see [LICENSE](LICENSE).
