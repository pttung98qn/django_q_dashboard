import base64
import json
from datetime import datetime

from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from django_q_dashboard import selectors

STATUS_COLORS = {
    "Working": "text-green-600 dark:text-green-400",
    "Idle": "text-blue-600 dark:text-blue-400",
    "Starting": "text-orange-600 dark:text-orange-400",
    "Stopping": "text-orange-600 dark:text-orange-400",
    "Stopped": "text-red-600 dark:text-red-400",
}


def _nowrap(text) -> str:
    return format_html('<span class="whitespace-nowrap">{}</span>', text)


def _short_timesince(dt: datetime) -> str:
    """Format elapsed time as abbreviated units, e.g. '2d 3h' or '5m'."""
    total_seconds = max(int((timezone.now() - dt).total_seconds()), 0)
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if not days and minutes:
        parts.append(f"{minutes}m")

    return f"{' '.join(parts[:2])} ago" if parts else "just now"


def _delete_queued_task_button(csrf_token: str | None, raw_payload: bytes) -> str:
    if not csrf_token:
        return ""
    payload_b64 = base64.b64encode(raw_payload).decode()
    return format_html(
        '<form method="post" action="{}" class="inline" '
        'onsubmit="return confirm(\'Remove this task from the queue?\')">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
        '<input type="hidden" name="payload" value="{}">'
        '<button type="submit" class="font-medium text-red-600 hover:underline dark:text-red-400">'
        "{}</button></form>",
        reverse("django_q:delete_queued_task"),
        csrf_token,
        payload_b64,
        "Delete",
    )


def _build_queued_tasks_table(queued_tasks: list[dict], csrf_token: str | None) -> dict:
    rows = [
        [
            task["id"][:8] if task["id"] else "—",
            task["name"],
            task["func"],
            format_html('<span class="break-words">{}</span>', task["args"]) if task["args"] else "—",
            format_html('<span class="break-words">{}</span>', task["kwargs"]) if task["kwargs"] else "—",
            task["group"] or "—",
            _nowrap(_short_timesince(task["queued_at"])) if task["queued_at"] else "—",
            _delete_queued_task_button(csrf_token, task["raw"]),
        ]
        for task in queued_tasks
    ]
    return {
        "headers": ["ID", "Task", "Function", "Args", "Kwargs", "Group", "Queued", "Actions"],
        "rows": rows,
    }


def _build_recent_failure_cards(recent_failures) -> list[dict]:
    return [
        {
            "task_link": format_html(
                '<a href="{}">{}</a>',
                reverse("admin:django_q_failure_change", args=(task.id,)),
                task.name or task.func,
            ),
            "when": _short_timesince(task.stopped),
            "result": str(task.result)[:300],
        }
        for task in recent_failures
    ]


def _build_upcoming_schedule_cards(upcoming_schedules) -> list[dict]:
    return [
        {
            "schedule_link": format_html(
                '<a href="{}">{}</a>',
                reverse("admin:django_q_schedule_change", args=(schedule.id,)),
                schedule.name or schedule.func,
            ),
            "type": schedule.get_schedule_type_display(),
            "next_run": schedule.next_run,
        }
        for schedule in upcoming_schedules
    ]


def _build_cluster_stats_table(cluster_stats: list[dict]) -> dict:
    rows = [
        [
            c["cluster_id"],
            c["host"],
            format_html(
                '<span class="{}">{}</span>',
                STATUS_COLORS.get(str(c["status"]), ""),
                c["status"],
            ),
            c["worker_count"],
        ]
        for c in cluster_stats
    ]
    return {"headers": ["Cluster", "Host", "Status", "Workers"], "rows": rows}


def build_queued_tasks_context(csrf_token: str | None = None) -> dict:
    """Queue depth + pending task list, used by both the full dashboard and its auto-refresh partial."""
    try:
        queue_depth = selectors.get_queue_depth()
        queued_tasks = selectors.get_queued_tasks()
        broker_error = None
    except Exception as e:
        queue_depth = None
        queued_tasks = []
        broker_error = str(e)

    return {
        "queue_depth": queue_depth,
        "queued_tasks": queued_tasks,
        "queued_tasks_table": _build_queued_tasks_table(queued_tasks, csrf_token),
        "broker_error": broker_error,
    }


def build_queue_dashboard_context(csrf_token: str | None = None) -> dict:
    """Queue/worker/task stats for the django-q admin app-index page."""
    queued_tasks_context = build_queued_tasks_context(csrf_token)

    cluster_stats = selectors.get_cluster_stats()
    recent_failures = selectors.get_recent_failures()
    upcoming_schedules = selectors.get_upcoming_schedules()
    task_summary = selectors.get_task_summary(days=7)

    chart_data = {
        "labels": task_summary["labels"],
        "datasets": [
            {
                "label": "Success",
                "data": task_summary["success_counts"],
                "borderColor": "#22c55e",
                "backgroundColor": "#22c55e33",
                "displayYAxis": True,
                "showPointLabels": True,
            },
            {
                "label": "Failed",
                "data": task_summary["failure_counts"],
                "borderColor": "#ef4444",
                "backgroundColor": "#ef444433",
                "showPointLabels": True,
            },
        ],
    }

    return {
        **queued_tasks_context,
        "cluster_stats": cluster_stats,
        "cluster_stats_table": _build_cluster_stats_table(cluster_stats),
        "task_summary": task_summary,
        "task_chart_data": json.dumps(chart_data),
        "recent_failure_cards": _build_recent_failure_cards(recent_failures),
        "upcoming_schedule_cards": _build_upcoming_schedule_cards(upcoming_schedules),
    }
