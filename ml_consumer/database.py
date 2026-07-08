"""Neo4j graph writer for the ML consumer.

Persists User and Comment nodes plus POSTED and REPLIES_TO relationships
as defined in PRD Section 3.3. Connection settings are read from
environment variables with defaults matching docker-compose.yml.
"""

import os
from typing import Any, Final

from neo4j import GraphDatabase, Driver

NEO4J_URI: Final[str] = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER: Final[str] = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD: Final[str] = os.getenv("NEO4J_PASSWORD", "testpassword")

_INSERT_COMMENT = """
MERGE (u:User {user_id: $user_id})
CREATE (c:Comment {
  event_id: $event_id,
  text: $text,
  timestamp: $timestamp,
  toxicity_score: $toxicity_score
})
CREATE (u)-[:POSTED]->(c)
"""

_INSERT_REPLY = """
MATCH (c:Comment {event_id: $event_id})
MERGE (parent:Comment {event_id: $reply_to_id})
CREATE (c)-[:REPLIES_TO]->(parent)
"""


class GraphDB:
    """Thin wrapper around the Neo4j Python driver for comment graph writes."""

    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
    ) -> None:
        self._driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        """Close the underlying driver connection pool."""
        self._driver.close()

    def __enter__(self) -> "GraphDB":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def insert_comment_graph(
        self,
        payload: dict[str, Any],
        scores: dict[str, float],
    ) -> None:
        """Write a scored comment and its relationships to the graph.

        Args:
            payload: ``raw_comments`` fields — ``event_id``, ``user_id``,
                ``text``, ``timestamp``, and optionally ``reply_to_id``.
            scores: Toxicity dimension scores from ``score_text`` for this
                comment. ``toxicity_score`` on the Comment node is taken
                from ``scores["toxicity"]``.
        """
        toxicity_score = float(scores.get("toxicity", 0.0))
        reply_to_id = payload.get("reply_to_id")

        with self._driver.session() as session:
            session.execute_write(
                self._write_comment,
                payload["event_id"],
                payload["user_id"],
                payload["text"],
                payload["timestamp"],
                toxicity_score,
                reply_to_id,
            )

    @staticmethod
    def _write_comment(
        tx: Any,
        event_id: str,
        user_id: str,
        text: str,
        timestamp: str,
        toxicity_score: float,
        reply_to_id: str | None,
    ) -> None:
        tx.run(
            _INSERT_COMMENT,
            event_id=event_id,
            user_id=user_id,
            text=text,
            timestamp=timestamp,
            toxicity_score=toxicity_score,
        )
        if reply_to_id:
            tx.run(
                _INSERT_REPLY,
                event_id=event_id,
                reply_to_id=reply_to_id,
            )


if __name__ == "__main__":
    sample_payload = {
        "event_id": "test-event-001",
        "user_id": "User_42",
        "text": "Smoke test comment for Neo4j graph writer",
        "timestamp": "2026-07-08T00:00:00Z",
        "reply_to_id": None,
    }
    sample_scores = {
        "toxicity": 0.12,
        "severe_toxicity": 0.01,
        "obscene": 0.02,
        "threat": 0.0,
        "insult": 0.05,
        "identity_attack": 0.01,
    }

    with GraphDB() as db:
        db.insert_comment_graph(sample_payload, sample_scores)
        print("Inserted test comment into Neo4j.")
