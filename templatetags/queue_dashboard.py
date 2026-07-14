from django import template
from django.template.context import RequestContext

from ..dashboard import build_queue_dashboard_context

register = template.Library()


@register.inclusion_tag("admin/django_q/queue_dashboard.html", takes_context=True)
def queue_dashboard(context: RequestContext) -> dict:
    return build_queue_dashboard_context(csrf_token=context.get("csrf_token"))
