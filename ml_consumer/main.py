"""ML consumer entry point: Kafka batch consume → score → Neo4j → publish.

Subscribes to ``raw_comments``, runs batched toxicity inference, writes the
social graph to Neo4j, and publishes ``scored_comments`` payloads. Offsets
are committed manually only after Neo4j and Kafka producer writes succeed.

Configuration (environment variables):
    KAFKA_BOOTSTRAP_SERVERS   Broker address (default ``localhost:9092``).
    KAFKA_CONSUMER_GROUP      Consumer group id (default ``ml_consumer_group``).
    RAW_TOPIC                 Input topic (default ``raw_comments``).
    SCORED_TOPIC              Output topic (default ``scored_comments``).
    BATCH_SIZE                Messages per consume batch (default ``16``).
    FLAG_THRESHOLD            Toxicity score for is_flagged (default ``0.5``).
    NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD  Neo4j connection (see database.py).
"""

import json
import os
import signal
from typing import Any, Final

from confluent_kafka import Consumer, KafkaError, Producer

from database import GraphDB
from inference import score_text
from model_loader import ToxicityModelLoader

BOOTSTRAP_SERVERS: Final[str] = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
CONSUMER_GROUP: Final[str] = os.getenv("KAFKA_CONSUMER_GROUP", "ml_consumer_group")
RAW_TOPIC: Final[str] = os.getenv("RAW_TOPIC", "raw_comments")
SCORED_TOPIC: Final[str] = os.getenv("SCORED_TOPIC", "scored_comments")
BATCH_SIZE: Final[int] = int(os.getenv("BATCH_SIZE", "16"))
CONSUME_TIMEOUT: Final[float] = float(os.getenv("CONSUME_TIMEOUT", "1.0"))
FLAG_THRESHOLD: Final[float] = float(os.getenv("FLAG_THRESHOLD", "0.5"))

_running = True


def _shutdown_handler(signum: int, frame: object) -> None:
    global _running
    _running = False
    print("\nShutdown signal received; finishing current work ...")


def _parse_payload(raw: bytes) -> dict[str, Any]:
    """Deserialize a raw_comments JSON message."""
    payload = json.loads(raw.decode("utf-8"))
    for field in ("event_id", "user_id", "text", "timestamp"):
        if field not in payload:
            raise ValueError(f"Missing required field {field!r} in payload")
    return payload


def _build_scored_payload(
    payload: dict[str, Any],
    scores: dict[str, float],
) -> dict[str, Any]:
    """Merge raw comment fields with scores and is_flagged for scored_comments."""
    return {
        "event_id": payload["event_id"],
        "user_id": payload["user_id"],
        "text": payload["text"],
        "timestamp": payload["timestamp"],
        "reply_to_id": payload.get("reply_to_id"),
        "scores": scores,
        "is_flagged": scores.get("toxicity", 0.0) >= FLAG_THRESHOLD,
    }


def process_batch(
    messages: list[Any],
    db: GraphDB,
    producer: Producer,
) -> None:
    """Score a batch, write to Neo4j, and publish to scored_comments."""
    payloads = [_parse_payload(msg.value()) for msg in messages]
    texts = [str(p["text"]) for p in payloads]
    scores_list = score_text(texts)

    for payload, scores in zip(payloads, scores_list):
        db.insert_comment_graph(payload, scores)
        scored = _build_scored_payload(payload, scores)
        producer.produce(
            SCORED_TOPIC,
            value=json.dumps(scored),
            key=payload["event_id"].encode("utf-8"),
        )

    producer.flush()
    print(f"Processed batch of {len(messages)} message(s)")


def main() -> None:
    """Run the consume → score → graph → publish loop."""
    global _running
    signal.signal(signal.SIGINT, _shutdown_handler)
    signal.signal(signal.SIGTERM, _shutdown_handler)

    print(
        f"ML consumer starting: {RAW_TOPIC} -> {SCORED_TOPIC} "
        f"at {BOOTSTRAP_SERVERS} (batch={BATCH_SIZE}, group={CONSUMER_GROUP})"
    )

    # Warm up model weights before entering the consume loop.
    ToxicityModelLoader().load()
    print("Model loaded.")

    consumer = Consumer(
        {
            "bootstrap.servers": BOOTSTRAP_SERVERS,
            "group.id": CONSUMER_GROUP,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    producer = Producer({"bootstrap.servers": BOOTSTRAP_SERVERS})

    consumer.subscribe([RAW_TOPIC])

    try:
        with GraphDB() as db:
            while _running:
                raw_messages = consumer.consume(
                    num_messages=BATCH_SIZE,
                    timeout=CONSUME_TIMEOUT,
                )
                if not raw_messages:
                    continue

                valid_messages = []
                for msg in raw_messages:
                    if msg is None:
                        continue
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            continue
                        raise RuntimeError(f"Consumer error: {msg.error()}")
                    valid_messages.append(msg)

                if not valid_messages:
                    continue

                process_batch(valid_messages, db, producer)
                consumer.commit(asynchronous=False)
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        producer.flush()
        consumer.close()
        print("ML consumer stopped.")


if __name__ == "__main__":
    main()
