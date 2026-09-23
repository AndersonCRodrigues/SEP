from django.views.generic import DetailView, ListView

from teacher.models import Teacher
from core.models import CustomUser

from .access import CoordinatorOnly


class CoordinatorTeachersView(CoordinatorOnly, ListView):
    template_name = "supervisor/list_users.html"
    context_object_name = "usuarios_listados"

    def get_queryset(self):
        return (
            Teacher.objects.filter(role=CustomUser.Role.PROFESSOR)
            .prefetch_related("acting_areas")
            .order_by("first_name", "last_name")
        )


class CoordinatorTeacherDetailView(CoordinatorOnly, DetailView):
    template_name = "supervisor/professor_detalhe.html"
    context_object_name = "professor"

    def get_queryset(self):
        return Teacher.objects.filter(role=CustomUser.Role.PROFESSOR).prefetch_related(
            "acting_areas"
        )
