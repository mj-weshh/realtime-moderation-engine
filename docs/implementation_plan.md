# Comprehensive Implementation Plan: Real-Time Moderation Engine

## Project Overview

This document outlines the chronological execution strategy for the realtime-moderation-engine. The project is divided into six sequential phases. Each phase establishes a foundation for the next, adhering to microservice architecture best practices.

**Estimated Timeline:** 3 Weeks (Aggressive Pace)  
**Pacing:** 2 Phases per Week  
**Methodology:** Agile-hybrid (Iterative development with strict Definitions of Done per phase).

---

# WEEK 1: Infrastructure & Data Ingestion

## Phase 1: Infrastructure Foundation & Local Environment

**Objective:** Set up the core networking and database infrastructure using Docker. No application code is written in this phase; we are just standing up the services.

### Technical Tasks

- [ ] Repository Setup: Clone realtime-moderation-engine. Define `.gitignore` for Python, Node.js, and large data files.

- [ ] Docker Compose Base: Create `docker-compose.yml`.

- [ ] Kafka Setup: Add Zookeeper (or KRaft) and Kafka broker to the compose file. Expose port `9092`.

- [ ] Neo4j Setup: Add Neo4j image. Configure environment variables for `NEO4J_AUTH` and map local volumes for data persistence. Expose ports `7474` (UI) and `7687` (Bolt).

- [ ] Network Configuration: Ensure all containers share a custom Docker network (e.g., `moderation_network`).

### Definition of Done (DoD)

- Running `docker-compose up` successfully starts Kafka and Neo4j without crashing.

- Can access the Neo4j browser UI at `localhost:7474`.

- Can successfully ping the Kafka broker using a CLI tool (like `kcat` or Kafka UI).

---

## Phase 2: Data Engineering (The Producer Service)

**Objective:** Build the Python service that streams the `civil_comments` dataset into Kafka, acting as our simulated "social network."

### Technical Tasks

- [ ] Data Acquisition: Download the `google/civil_comments` dataset (test split). Save it locally (ensure this path is `.gitignored`).

- [ ] Project Setup: Initialize a Python virtual environment (`venv`). Install `pandas`, `confluent-kafka` (or `kafka-python`).

- [ ] Data Transformation: Write a script to load the dataset into a Pandas DataFrame.

- [ ] Synthetic Graph Generation: Write logic to randomly assign synthetic `user_ids` and `reply_to_ids` to the comments to simulate conversation threads.

- [ ] Kafka Publisher: Implement the Kafka Producer logic. Convert rows to JSON and publish to the `raw_comments` topic.

- [ ] Rate Limiting: Add a sleep timer to publish a configurable number of messages per second (e.g., 50 msg/sec).

- [ ] Dockerization: Write a Dockerfile for this service and add it to `docker-compose.yml`.

### Definition of Done (DoD)

- The Producer service runs in a Docker container.

- Messages are visibly streaming into the Kafka `raw_comments` topic at the configured rate.

- Payload JSON strictly matches the schema defined in the PRD (Section 3.2).

---

# WEEK 2: AI Brain & Real-Time Bridge

## Phase 3: Machine Learning Inference (The Consumer Service)

**Objective:** Build the brain. Consume raw messages, run inference via a pre-trained Hugging Face model, and route the results.

### Technical Tasks

- [ ] Project Setup: Initialize a new Python service directory. Install `torch`, `transformers`, `confluent-kafka`, `neo4j`.

- [ ] Model Initialization: Write a script to download and cache a toxicity-classification model (e.g., `unitary/toxic-bert` or a DistilBERT equivalent) from Hugging Face.

- [ ] Inference Logic: Write the Python function that takes a list of text strings, tokenizes them, runs them through the model, and extracts the float scores for toxicity labels.

- [ ] Kafka Consumer: Implement a consumer that subscribes to `raw_comments`. Implement batching (e.g., pull 16 messages at a time).

- [ ] Neo4j Integration: Write Cypher queries to inject the node/edge data. (Use Neo4j Python Driver).

  - MERGE User node.
  - CREATE Comment node with scores.
  - CREATE relationships (`POSTED`, `REPLIES_TO`).

- [ ] Kafka Producer (Output): Publish the combined payload (original message + scores + `is_flagged` boolean) to the `scored_comments` topic.

- [ ] Dockerization: Create a Dockerfile. Ensure model weights are volume-mapped so they aren't re-downloaded on every build.

### Definition of Done (DoD)

- Consumer reads from `raw_comments` and processes batches without memory leaks.

- Neo4j database correctly populates with nodes and relationships.

- Scored JSON payloads are verified in the `scored_comments` Kafka topic.

---

## Phase 4: Backend API & WebSockets

**Objective:** Build the bridge between the high-throughput backend and the browser.

### Technical Tasks

- [ ] Project Setup: Initialize a Node.js project. Install `express`, `ws` (or `socket.io`), and `kafkajs`.

- [ ] Kafka Consumer (Node.js): Subscribe to the `scored_comments` topic.

- [ ] Filtering Logic: Implement logic to drop messages where `toxicity < 0.5` to prevent overwhelming the frontend.

- [ ] WebSocket Server: Initialize the WS server. Write the event emitter that broadcasts the filtered, flagged payloads to all connected UI clients.

- [ ] Dockerization: Write Dockerfile for the Node service and add to Compose.

### Definition of Done (DoD)

- Node.js server connects to Kafka.

- A simple local WebSocket client (e.g., Postman or a test script) can connect to the server and instantly receive JSON payloads of toxic comments.

---

# WEEK 3: Visual Analytics & Deployment Polish

## Phase 5: Next.js Frontend Dashboard

**Objective:** Build the real-time command center UI.

### Technical Tasks

- [ ] Project Setup: `npx create-next-app@latest` (Use TypeScript, Tailwind CSS).

- [ ] UI Layout: Design a dark-mode, high-contrast dashboard layout (Header, Live Feed column, Graph visualization main area).

- [ ] WebSocket Client Context: Create a React Context or custom hook (`useWebSocket`) to manage the persistent connection to the Node.js backend.

- [ ] Live Feed Component: Create a scrolling, auto-updating list of toxic comments. Implement color-coding (e.g., Yellow for >0.5, Red for >0.8 severe toxicity).

- [ ] Graph Visualization: Integrate `react-force-graph-2d` or `d3.js`.

  - Map incoming WebSocket data into a `nodes` array and `links` array.
  - Render the real-time clustering of users and comments.

- [ ] State Management: Implement strict limits on React state (e.g., keep only the last 200 nodes in memory to prevent the browser from crashing).

- [ ] Dockerization: Write a multi-stage Dockerfile for the Next.js app and add to Compose.

### Definition of Done (DoD)

- UI cleanly renders without errors.

- Dashboard visually updates in real-time as messages flow from the Producer -> ML Consumer -> Node Backend -> Next.js.

- Browser memory remains stable over a 10-minute continuous run.

---

## Phase 6: E2E Testing, Optimization & Polish

**Objective:** Make it production-grade and portfolio-ready.

### Technical Tasks

- [ ] Latency Audit: Measure the time from data generation to UI render. Optimize Kafka batch sizes if latency exceeds 2 seconds.

- [ ] Fault Tolerance Test: Manually kill the ML Consumer container while the Producer is running. Restart it and verify it resumes processing from the exact offset it left off.

- [ ] Documentation: Write an immaculate `README.md`.

  - Include Architecture Diagram.
  - Step-by-step instructions: "How to run locally."
  - Explanation of the Machine Learning pipeline and graph logic.

- [ ] Code Cleanup: Ensure standard formatting (Prettier/Black), remove dead code, and verify SOLID principles.

### Definition of Done (DoD)

- `docker-compose up --build` launches the entire 5-container ecosystem flawlessly from a cold start.

- The repository is public, documented, and ready for interview presentations.