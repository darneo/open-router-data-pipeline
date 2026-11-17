from __future__ import annotations
import json
from confluent_kafka import KafkaException, Producer
from src.config import BOOTSTRAP_SERVERS, DATA_DIR, TOPIC


def main() -> None:
    source = DATA_DIR / "models.jsonl"
    records = [
        json.loads(line)
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    delivery = {"sent": 0, "errors": []}

    def on_delivery(error, message) -> None:
        if error is not None:
            delivery["errors"].append(str(error))
        else:
            delivery["sent"] += 1

    producer = Producer(
        {
            "bootstrap.servers": BOOTSTRAP_SERVERS,
            "client.id": "openrouter-models-producer",
            "enable.idempotence": True,
            "message.timeout.ms": 30000,
        }
    )
    try:
        for record in records:
            key = str(record["model_id"]).encode("utf-8")
            value = json.dumps(record, ensure_ascii=False).encode("utf-8")
            while True:
                try:
                    producer.produce(TOPIC, key=key, value=value, callback=on_delivery)
                    break
                except BufferError:
                    producer.poll(0.5)
            producer.poll(0)
        remaining = producer.flush(60)
    except KafkaException:
        producer.flush(10)
        raise

    if remaining:
        raise RuntimeError(f"Producer flush timed out with {remaining} messages pending")
    if delivery["errors"]:
        raise RuntimeError(
            f"Kafka failed to deliver {len(delivery['errors'])} messages; "
            f"first error: {delivery['errors'][0]}"
        )
    if delivery["sent"] != len(records):
        raise RuntimeError(
            f"Expected to publish {len(records)} records, got {delivery['sent']}"
        )



if __name__ == "__main__":
    main()
