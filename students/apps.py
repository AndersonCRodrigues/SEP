from django.apps import AppConfig


class StudentsConfig(AppConfig):
    name = 'students'
    verbose_name = "Alunos"

    def ready(self):
        from . import signals  # noqa: F401
