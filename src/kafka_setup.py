from confluent_kafka.admin import AdminClient, NewTopic

from src.config import BOOTSTRAP_SERVERS, TOPIC


def reset_topic() -> None:
    admin = AdminClient({"bootstrap.servers": BOOTSTRAP_SERVERS})
    metadata = admin.list_topics(timeout=10)
    if TOPIC in metadata.topics:
        deletion = admin.delete_topics([TOPIC], operation_timeout=30)[TOPIC]
        deletion.result(timeout=40)
        print(f"Deleted old topic data: {TOPIC}")

    creation = admin.create_topics(
        [NewTopic(TOPIC, num_partitions=1, replication_factor=1)]
    )[TOPIC]
    creation.result(timeout=40)
    print(f"Created clean topic: {TOPIC}")


if __name__ == "__main__":
    reset_topic()
