# Real-Time Moderation Engine



A high-throughput, distributed data pipeline that ingests simulated social media traffic, scores it for **toxicity and misinformation in real time**, maps malicious network clusters in a graph database, and (in upcoming phases) streams flagged alerts to a live command-center dashboard.



!!! info "Project status"

    **Week 2 in progress** — the ML inference consumer is live (Kafka batch scoring, Neo4j graph writes, `scored_comments` publishing). The WebSocket API and Next.js frontend are under active development.



## The Pipeline at a Glance



```mermaid

flowchart LR

    dataset[("civil_comments<br/>dataset")] --> producer[producer_service]

    producer -- "raw_comments" --> kafka[(Kafka)]

    kafka --> consumer[ml_consumer<br/>toxicity inference]

    consumer -- "graph writes" --> neo4j[(Neo4j)]

    consumer -- "scored_comments" --> kafka

    kafka -. "Week 2" .-> ws[backend_api<br/>WebSockets]

    ws -. "Week 3" .-> ui[Next.js dashboard]

```



1. The **producer** enriches real comments from the [`google/civil_comments`](https://huggingface.co/datasets/google/civil_comments) dataset with a synthetic social graph (users, reply chains) and streams them into Kafka at ~50 msg/sec.

2. The **ML consumer** runs batched transformer inference, writes conversation graphs to Neo4j, and re-publishes scored payloads to `scored_comments`.

3. The **WebSocket bridge** *(upcoming)* filters for flagged content and pushes it to connected clients.

4. The **dashboard** *(Week 3)* renders a live feed and force-directed graph of toxic clusters.



## Where to Go Next



| Page | What you'll find |

|---|---|

| [Architecture](architecture.md) | Why Kafka, why KRaft, why Neo4j — and how the pieces connect |

| [Local Setup](local_setup.md) | Step-by-step guide from clone to running stack |

| [Data Pipeline](data_pipeline.md) | Topics, payload schemas, and the synthetic graph generator |

| [ML Inference](ml_inference.md) | Model, Kafka loop, Neo4j writes, env vars, and fault tolerance |

| [PRD](PRD.md) | The full product requirements document |

| [Implementation Plan](implementation_plan.md) | The six-phase build roadmap |



## Tech Stack



**Python 3.13** · **Apache Kafka (KRaft)** · **Neo4j 5** · **PyTorch + Hugging Face Transformers** · **Docker Compose** · *upcoming:* Node.js WebSockets, Next.js + Tailwind

