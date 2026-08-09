from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "audit"
    verbose_name = "Auditoria"

    def ready(self):
        from . import signals  # noqa: F401
