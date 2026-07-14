from datetime import timedelta

from django.db import Error as DBError, transaction
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from django_q.brokers import get_broker
from django_q.models import Failure, Schedule, Success
from django_q.signing import BadSignature, SignedPackage
from django_q.status import Stat
from django_q.utils import get_func_repr


def get_queue_depth() -> int:
    """Number of tasks currently waiting in the Redis broker queue."""
    return get_broker().queue_size()


def get_queued_tasks(limit: int = 20) -> list[dict]:
    """Pending tasks sitting in the Redis broker list, oldest first."""
    broker = get_broker()
    raw_items = broker.connection.lrange(broker.list_key, 0, limit - 1)
    tasks = []
    for raw in raw_items:
        try:
            task = SignedPackage.loads(raw)
        except BadSignature:
            continue
        tasks.append({
            "id": task.get("id"),
            "name": task.get("name"),
            "func": get_func_repr(task.get("func")),
            "args": task.get("args"),
            "kwargs": task.get("kwargs"),
            "group": task.get("group"),
            "queued_at": task.get("started"),
            "raw": raw,
        })
    return tasks


def get_cluster_stats() -> list[dict]:
    """Live status of running django-q clusters/workers, read from the broker."""
    stats = []
    for stat in Stat.get_all():
        stats.append({
            "cluster_id": stat.cluster_id,
            "host": stat.host,
            "status": stat.status,
            "worker_count": len(stat.workers),
            "uptime_seconds": stat.uptime() if stat.tob else 0,
        })
    return stats


def get_task_summary(days: int = 7) -> dict:
    """Success/failure totals and a daily breakdown for the last `days` days."""
    try:
        with transaction.atomic():
            return _get_task_summary(days)
    except DBError:
        # TruncDate() below sends the currently active Django timezone name
        # straight to the database via `AT TIME ZONE`. If the host app
        # activated a timezone name (from a cookie/geo-IP guess) that this
        # database's tzdata doesn't recognize (e.g. legacy alias
        # "Asia/Saigon" on a trimmed Postgres install), the query fails.
        # Retry once in UTC, which every Postgres install understands.
        with timezone.override("UTC"):
            return _get_task_summary(days)


def _get_task_summary(days: int) -> dict:
    since = timezone.now() - timedelta(days=days)

    success_by_day = dict(
        Success.objects.filter(stopped__gte=since)
        .annotate(day=TruncDate("stopped"))
        .values("day")
        .annotate(count=Count("id"))
        .values_list("day", "count")
    )
    failure_by_day = dict(
        Failure.objects.filter(stopped__gte=since)
        .annotate(day=TruncDate("stopped"))
        .values("day")
        .annotate(count=Count("id"))
        .values_list("day", "count")
    )

    labels = [(since.date() + timedelta(days=i)) for i in range(days + 1)]
    return {
        "labels": [d.strftime("%b %d") for d in labels],
        "success_counts": [success_by_day.get(d, 0) for d in labels],
        "failure_counts": [failure_by_day.get(d, 0) for d in labels],
        "total_success": sum(success_by_day.values()),
        "total_failure": sum(failure_by_day.values()),
    }


def get_recent_failures(limit: int = 8):
    return Failure.objects.order_by("-stopped")[:limit]


def get_upcoming_schedules(limit: int = 8):
    return Schedule.objects.order_by("next_run")[:limit]
