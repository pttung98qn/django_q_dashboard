from django_q.brokers import get_broker


def delete_queued_task(raw_payload: bytes) -> bool:
    """Remove one matching task from the Redis broker queue. Returns True if a task was removed."""
    broker = get_broker()
    removed = broker.connection.lrem(broker.list_key, 1, raw_payload)
    return bool(removed)
