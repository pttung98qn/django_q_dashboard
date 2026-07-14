from django.conf import settings
from django.contrib import admin
from django.utils.module_loading import import_string
from django_q.admin import FailAdmin, ScheduleAdmin, TaskAdmin
from django_q.models import Failure, Schedule, Success


def _get_admin_base_class():
    """Host project's own ModelAdmin base, set via DJANGO_Q_DASHBOARD_ADMIN_BASE (dotted path).

    Falls back to plain unfold.admin.ModelAdmin so the package works standalone
    in a project that doesn't define one.
    """
    dotted_path = getattr(settings, "DJANGO_Q_DASHBOARD_ADMIN_BASE", None)
    if dotted_path:
        return import_string(dotted_path)
    from unfold.admin import ModelAdmin
    return ModelAdmin


_AdminBase = _get_admin_base_class()


class CustomScheduleAdmin(ScheduleAdmin, _AdminBase):
    pass


class CustomTaskAdmin(TaskAdmin, _AdminBase):
    pass


class CustomFailAdmin(FailAdmin, _AdminBase):
    pass


admin.site.unregister(Success)
admin.site.unregister(Failure)
admin.site.unregister(Schedule)

admin.site.register(Schedule, CustomScheduleAdmin)
admin.site.register(Success, CustomTaskAdmin)
admin.site.register(Failure, CustomFailAdmin)
