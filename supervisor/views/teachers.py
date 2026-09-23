from django.db.models import Count, Q
from django.views.generic import DetailView, ListView

from areas.models import AreaActing
from core.models import CustomUser
from teacher.models import Teacher

from .access import CoordinatorOnly

COLUMNS = ("Nome:", "Área de atuação:", "Alunos vinculados:", "Status:", "")


class CoordinatorTeachersView(CoordinatorOnly, ListView):
    template_name = "supervisor/list_users.html"
    context_object_name = "usuarios_listados"

    def get_queryset(self):
        professores = (
            Teacher.objects.filter(role=CustomUser.Role.PROFESSOR)
            .prefetch_related("acting_areas")
            .annotate(advisees=Count("current_advisees", distinct=True))
            .order_by("first_name", "last_name")
        )

        busca = self.request.GET.get("q", "").strip()
        if busca:
            professores = professores.filter(
                Q(first_name__icontains=busca) | Q(last_name__icontains=busca)
            )

        area = self.request.GET.get("area", "")
        if area.isdigit():
            professores = professores.filter(acting_areas__pk=area)

        return professores

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["columns"] = COLUMNS
        context["search"] = self.request.GET.get("q", "").strip()
        context["area_filter"] = self.request.GET.get("area", "")
        context["areas"] = AreaActing.objects.order_by("nome")
        context["teachers"] = [
            {
                "teacher": professor,
                "areas": ", ".join(area.nome for area in professor.acting_areas.all()),
                "advisees": professor.advisees,
                "label": "Ativo" if professor.advisees else "Sem alunos",
                "level": "success" if professor.advisees else "warning",
            }
            for professor in context["usuarios_listados"]
        ]
        return context


class CoordinatorTeacherDetailView(CoordinatorOnly, DetailView):
    template_name = "supervisor/professor_detalhe.html"
    context_object_name = "professor"

    def get_queryset(self):
        return Teacher.objects.filter(role=CustomUser.Role.PROFESSOR).prefetch_related(
            "acting_areas"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["advisees"] = context["professor"].current_advisees.order_by(
            "first_name", "last_name"
        )
        return context
