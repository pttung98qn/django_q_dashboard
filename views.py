import base64
import binascii

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from django_q_dashboard import services
from django_q_dashboard.dashboard import build_queued_tasks_context


@staff_member_required
@require_GET
def queued_tasks_card(request: HttpRequest) -> HttpResponse:
    context = build_queued_tasks_context(csrf_token=get_token(request))
    return render(request, "admin/django_q/_queued_tasks_poll_response.html", context)


@staff_member_required
@require_POST
def delete_queued_task(request: HttpRequest) -> HttpResponseRedirect:
    redirect_url = reverse("admin:app_list", kwargs={"app_label": "django_q"})

    try:
        raw_payload = base64.b64decode(request.POST.get("payload", ""), validate=True)
    except (binascii.Error, ValueError):
        messages.error(request, "Invalid task payload.")
        return HttpResponseRedirect(redirect_url)

    if services.delete_queued_task(raw_payload):
        messages.success(request, "Task removed from the queue.")
    else:
        messages.warning(request, "Task was no longer in the queue.")

    return HttpResponseRedirect(redirect_url)
