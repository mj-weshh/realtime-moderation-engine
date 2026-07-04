"""Producer service entry point.

Streams the civil_comments test subset into the Kafka ``raw_comments``
topic as a simulated social-media feed: each comment is enriched with a
synthetic event ID, author, timestamp, and (for ~15-20% of messages) a
reply link to a recent event, then published at a configurable rate.

Payloads strictly follow the ``raw_comments`` schema from PRD Section 3.2.

Configuration (environment variables):
    KAFKA_BOOTSTRAP_SERVERS  Broker address (default ``localhost:9092``).
    MESSAGES_PER_SECOND      Publish rate limit (default ``50``).
"""

import json
import os
import random
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

import pandas as pd
from confluent_kafka import Message, Producer

SUBSET_PATH: Final[Path] = (
    Path(__file__).resolve().parents[1] / "data" / "comments_subset.parquet"
)

TOPIC: Final[str] = "raw_comments"
BOOTSTRAP_SERVERS: Final[str] = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
MESSAGES_PER_SECOND: Final[float] = float(os.getenv("MESSAGES_PER_SECOND", "50"))

# Synthetic social graph parameters.
USER_POOL: Final[tuple[str, ...]] = tuple(f"User_{i}" for i in range(1, 1001))
REPLY_PROBABILITY: Final[float] = 0.175  # midpoint of the 15-20% spec
RECENT_EVENTS_MAXLEN: Final[int] = 100


def enrich_data(text: str, recent_event_ids: deque[str]) -> dict[str, str | None]:
    """Wrap a raw comment in a synthetic social-media event payload.

    Assigns a fresh UUID event ID and a random author from the user pool.
    With probability ``REPLY_PROBABILITY`` the comment becomes a reply to
    a randomly chosen recent event, simulating conversation threads.

    Args:
        text: The raw comment text.
        recent_event_ids: Bounded deque of recently generated event IDs.
            Mutated in place: the new event ID is appended so later
            comments can reply to this one.

    Returns:
        A payload dict matching the PRD 3.2 ``raw_comments`` schema.
    """
    event_id = str(uuid.uuid4())

    reply_to_id: str | None = None
    if recent_event_ids and random.random() < REPLY_PROBABILITY:
        reply_to_id = random.choice(list(recent_event_ids))

    payload: dict[str, str | None] = {
        "event_id": event_id,
        "user_id": random.choice(USER_POOL),
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "reply_to_id": reply_to_id,
    }
    recent_event_ids.append(event_id)
    return payload


def delivery_report(err: object, msg: Message) -> None:
    """Per-message delivery callback invoked by the Kafka client."""
    if err is not None:
        print(f"Delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [partition {msg.partition()}]")


def load_comments(path: Path = SUBSET_PATH) -> pd.DataFrame:
    """Load the local comments subset into a DataFrame.

    Raises:
        FileNotFoundError: If the subset has not been generated yet
            (run ``fetch_data.py`` first).
    """
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run 'python fetch_data.py' to download the data."
        )
    return pd.read_parquet(path)


def main() -> None:
    """Stream enriched comments to Kafka at the configured rate."""
    df = load_comments()
    print(
        f"Streaming {len(df):,} comments to '{TOPIC}' at "
        f"{BOOTSTRAP_SERVERS} (~{MESSAGES_PER_SECOND:g} msg/sec)"
    )

    producer = Producer({"bootstrap.servers": BOOTSTRAP_SERVERS})
    recent_event_ids: deque[str] = deque(maxlen=RECENT_EVENTS_MAXLEN)
    delay_seconds = 1.0 / MESSAGES_PER_SECOND

    try:
        for text in df["text"]:
            payload = enrich_data(str(text), recent_event_ids)
            producer.produce(
                TOPIC,
                value=json.dumps(payload),
                callback=delivery_report,
            )
            # Service the delivery callbacks without blocking.
            producer.poll(0)
            time.sleep(delay_seconds)
    except KeyboardInterrupt:
        print("\nInterrupted; flushing outstanding messages ...")
    finally:
        producer.flush()
        print("Producer flushed. Done.")


if __name__ == "__main__":
    main()
