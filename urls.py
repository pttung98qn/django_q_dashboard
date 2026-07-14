from django.urls import path

from django_q_dashboard import views

app_name = "django_q"

urlpatterns = [
    path("queue/delete-task/", views.delete_queued_task, name="delete_queued_task"),
    path("queue/queued-tasks-card/", views.queued_tasks_card, name="queued_tasks_card"),
]
