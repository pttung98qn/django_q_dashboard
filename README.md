# django-q-dashboard

Unfold-styled admin dashboard for [django-q2](https://django-q2.readthedocs.io/): queue depth, worker/cluster status, a 7-day success/failure chart, the live Redis queue with delete, recent failures and upcoming schedules — all on the `django_q` app's admin index page.

## Install

```bash
pip install "git+https://github.com/<you>/django-q-dashboard.git@v0.1.0#subdirectory=django_q_dashboard"
```

## Setup

```python
INSTALLED_APPS = [
    ...
    "django_q",
    "django_q_dashboard",  # after django_q
    ...
]
```

```python
urlpatterns = [
    ...
    path("django-q/", include("django_q_dashboard.urls")),
]
```

Visit `/admin/django_q/` for the dashboard.

## Optional: reuse your own ModelAdmin base

By default the `Success`/`Failure`/`Schedule` admin classes extend `unfold.admin.ModelAdmin`. To extend your project's own base admin class instead:

```python
DJANGO_Q_DASHBOARD_ADMIN_BASE = "myproject.admin.BaseAdmin"
```
