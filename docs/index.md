# Real-Time Moderation Engine

A high-throughput, distributed data pipeline that ingests simulated social media traffic, scores it for **toxicity and misinformation in real time**, maps malicious network clusters in a graph database, and streams flagged alerts to connected clients over WebSockets.

!!! info "Project status"
    **Complete** — the full stack runs with a single `docker-compose up` command: Kafka producer, ML inference consumer, Neo4j graph writes, WebSocket broadcast, and the Next.js dashboard at <http://localhost:3000>.

## The Pipeline at a Glance

```mermaid
flowchart LR
    dataset[("civil_comments<br/>dataset")] --> producer[producer_service]
    producer -- "raw_comments" --> kafka[(Kafka)]
    kafka --> consumer[ml_consumer<br/>toxicity inference]
    consumer -- "graph writes" --> neo4j[(Neo4j)]
    consumer -- "scored_comments" --> kafka
    kafka --> ws[websocket_api<br/>filter + broadcast]
    ws -- "WebSocket :8081" --> ui[Next.js dashboard]
    browser[Browser] -- "HTTP :3000" --> ui
```

1. The **producer** enriches real comments from the [`google/civil_comments`](https://huggingface.co/datasets/google/civil_comments) dataset with a synthetic social graph (users, reply chains) and streams them into Kafka at ~50 msg/sec.
2. The **ML consumer** runs batched transformer inference, writes conversation graphs to Neo4j, and re-publishes scored payloads to `scored_comments`.
3. The **WebSocket API** consumes `scored_comments`, filters for flagged toxicity, and broadcasts matching payloads to connected clients on `:8081`.
4. The **dashboard** renders a live alert feed and force-directed graph of toxic clusters at <http://localhost:3000>.

## Where to Go Next

| Page | What you'll find |
|---|---|
| [Architecture](architecture.md) | Why Kafka, why KRaft, why Neo4j — and how the pieces connect |
| [Local Setup](local_setup.md) | Step-by-step guide from clone to running stack |
| [Data Pipeline](data_pipeline.md) | Topics, payload schemas, and the synthetic graph generator |
| [ML Inference](ml_inference.md) | Model, Kafka loop, Neo4j writes, env vars, and fault tolerance |
| [WebSocket API](websocket_api.md) | Kafka consumer, filtering, WebSocket broadcast, and E2E testing |
| [Frontend Dashboard](frontend.md) | Live feed, force graph, WebSocket hook, Docker, and state limits |
| [PRD](PRD.md) | The full product requirements document |
| [Implementation Plan](implementation_plan.md) | The six-phase build roadmap |

## Tech Stack

**Python 3.13** · **Node.js 18 + Express + ws + kafkajs** · **Next.js 16 + Tailwind v4 + react-force-graph-2d** · **Apache Kafka (KRaft)** · **Neo4j 5** · **PyTorch + Hugging Face Transformers** · **Docker Compose**
