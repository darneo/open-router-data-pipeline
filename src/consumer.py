"""Read exactly the number of records present in the current source JSONL."""

from __future__ import annotations

import json
import time
import uuid

from confluent_kafka import Consumer, KafkaError

from src.config import BOOTSTRAP_SERVERS, DATA_DIR, TOPIC


def expected_message_count() -> int:
    source = DATA_DIR / "models.jsonl"
    return sum(1 for line in source.open(encoding="utf-8") if line.strip())


def main() -> None:
    expected = expected_message_count()
    if expected == 0:
        raise RuntimeError("models.jsonl has no messages to consume")

    consumer = Consumer(
        {
            "bootstrap.servers": BOOTSTRAP_SERVERS,
            "group.id": f"openrouter-models-{uuid.uuid4().hex}",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "enable.partition.eof": False,
        }
    )
    records = []
    errors = []
    deadline = time.monotonic() + max(180, expected * 0.5)
    consumer.subscribe([TOPIC])
    try:
        while len(records) < expected and time.monotonic() < deadline:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                if message.error().code() != KafkaError._PARTITION_EOF:
                    errors.append(str(message.error()))
                continue
            try:
                records.append(json.loads(message.value().decode("utf-8")))
            except (UnicodeDecodeError, json.JSONDecodeError) as error:
                errors.append(f"message at offset {message.offset()}: {error}")
    finally:
        consumer.close()

    if len(records) != expected:
        detail = f"; first Kafka/JSON error: {errors[0]}" if errors else ""
        raise RuntimeError(
            f"Expected {expected} messages, consumed {len(records)} before timeout{detail}"
        )
    if errors:
        raise RuntimeError(f"Consumer encountered errors: {errors[0]}")

    output = DATA_DIR / "consumed_models.jsonl"
    temporary = output.with_suffix(".jsonl.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    temporary.replace(output)



if __name__ == "__main__":
    main()
