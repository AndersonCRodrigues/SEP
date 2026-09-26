from django.db.models import Q
from django.views.generic import DetailView, ListView

from areas.models import AreaActing
from students.models import Student

from .access import CoordinatorOnly

COLUMNS = ("Nome:", "Orientador:", "Fase do estágio:", "Status:", "")


class CoordinatorStudentsView(CoordinatorOnly, ListView):
    template_name = "supervisor/alunos.html"
    context_object_name = "alunos"

    def get_queryset(self):
        alunos = Student.objects.select_related("current_advisor").order_by(
            "first_name", "last_name"
        )

        busca = self.request.GET.get("q", "").strip()
        if busca:
            alunos = alunos.filter(
                Q(first_name__icontains=busca)
                | Q(last_name__icontains=busca)
                | Q(matricula__icontains=busca)
            )

        area = self.request.GET.get("area", "")
        if area.isdigit():
            alunos = alunos.filter(current_advisor__acting_areas__pk=area)

        return alunos.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["columns"] = COLUMNS
        context["search"] = self.request.GET.get("q", "").strip()
        context["area_filter"] = self.request.GET.get("area", "")
        context["areas"] = AreaActing.objects.order_by("nome")
        context["students"] = [
            {
                "student": aluno,
                "advisor": (
                    aluno.current_advisor.get_full_name()
                    if aluno.current_advisor
                    else "Sem orientador"
                ),
                "stage": aluno.get_stage_display(),
                "label": "Vinculado" if aluno.current_advisor else "Sem orientador",
                "level": "success" if aluno.current_advisor else "warning",
            }
            for aluno in context["alunos"]
        ]
        return context


class CoordinatorStudentDetailView(CoordinatorOnly, DetailView):
    template_name = "supervisor/aluno_detalhe.html"
    context_object_name = "aluno"

    def get_queryset(self):
        return Student.objects.select_related("current_advisor")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["open_cases"] = context["aluno"].open_cases.select_related("patient")
        return context
