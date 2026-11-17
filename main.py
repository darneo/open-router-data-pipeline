"""Run the complete OpenRouter models data pipeline."""

from __future__ import annotations

import json
import csv
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.admin import AdminClient

from src.config import BOOTSTRAP_SERVERS, DATA_DIR, PROJECT_DIR, TOPIC
from src.kafka_setup import reset_topic


def wait_for_broker(timeout_seconds: int = 90) -> None:
    """Wait until the broker answers metadata requests."""
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            AdminClient({"bootstrap.servers": BOOTSTRAP_SERVERS}).list_topics(
                timeout=5
            )
            return
        except Exception as error:  # broker may need several seconds to start
            last_error = error
            time.sleep(2)
    raise RuntimeError(f"Kafka broker did not become ready: {last_error}")


def run_module(module: str, title: str) -> None:
    print(f"\n=== {title} ===", flush=True)
    subprocess.run(
        [sys.executable, "-u", "-m", module],
        cwd=PROJECT_DIR,
        check=True,
    )


def verify_counts() -> dict[str, int]:
    def jsonl_count(filename: str) -> int:
        with (DATA_DIR / filename).open(encoding="utf-8") as source:
            return sum(1 for line in source if line.strip())

    collected = jsonl_count("models.jsonl")
    consumed = jsonl_count("consumed_models.jsonl")
    valid = jsonl_count("valid_models.jsonl")
    invalid = jsonl_count("invalid_models.jsonl")
    with (DATA_DIR / "processed_models.csv").open(encoding="utf-8", newline="") as source:
        processed = sum(1 for _ in csv.DictReader(source))
    with sqlite3.connect(DATA_DIR / "models.db") as connection:
        stored = connection.execute("SELECT COUNT(*) FROM models").fetchone()[0]
    kafka_consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "group.id": "openrouter-count-verification",
        "enable.auto.commit": False,
    })
    try:
        topic_metadata = AdminClient({"bootstrap.servers": BOOTSTRAP_SERVERS}).list_topics(
            TOPIC, timeout=10
        ).topics[TOPIC]
        published = 0
        for partition_id in topic_metadata.partitions:
            low, high = kafka_consumer.get_watermark_offsets(
                TopicPartition(TOPIC, partition_id), timeout=10
            )
            published += high - low
    finally:
        kafka_consumer.close()
    counts = {
        "collected": collected,
        "published": published,
        "consumed": consumed,
        "valid": valid,
        "invalid": invalid,
        "processed": processed,
        "stored": stored,
    }
    if not (counts["collected"] == counts["published"] == counts["consumed"]):
        raise RuntimeError(f"API/Kafka counts differ: {counts}")
    if counts["valid"] + counts["invalid"] != counts["consumed"]:
        raise RuntimeError(f"Validation counts do not add up: {counts}")
    if counts["processed"] != counts["valid"]:
        raise RuntimeError(f"Cleaning changed the valid count unexpectedly: {counts}")
    if counts["stored"] != counts["processed"]:
        raise RuntimeError(f"SQLite count differs from processed rows: {counts}")
    return counts


def main() -> None:
    compose = subprocess.run(
        ["docker", "compose", "up", "-d"],
        cwd=PROJECT_DIR,
        text=True,
        capture_output=True,
    )
    if compose.returncode:
        raise RuntimeError(
            "Could not start Kafka with Docker Compose.\n"
            f"{compose.stdout}\n{compose.stderr}"
        )
    print(compose.stdout.strip() or "Kafka service is running.", flush=True)
    wait_for_broker()

    run_module("src.api_client", "1/7 Collect current API data")
    reset_topic()
    run_module("src.producer", "2/7 Publish JSON records to Kafka")
    run_module("src.consumer", "3/7 Consume the complete topic")
    run_module("src.validator", "4/7 Validate records with Pandera")
    run_module("src.cleaner", "5/7 Clean and transform with pandas/NumPy")
    run_module("src.loader", "6/7 Load SQLite and verify idempotency")
    run_module("src.analysis", "7/7 Run EDA and save figures")

    counts = verify_counts()
    print("\nPipeline verified successfully.")
    print(json.dumps(counts, indent=2))
    print(f"Kafka topic: {TOPIC}")


if __name__ == "__main__":
    main()
