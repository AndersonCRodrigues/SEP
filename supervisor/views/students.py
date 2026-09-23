from django.views.generic import DetailView, ListView

from students.models import Student

from .access import CoordinatorOnly


class CoordinatorStudentsView(CoordinatorOnly, ListView):
    template_name = "supervisor/alunos.html"
    context_object_name = "alunos"

    def get_queryset(self):
        return Student.objects.select_related("current_advisor").order_by(
            "first_name", "last_name"
        )


class CoordinatorStudentDetailView(CoordinatorOnly, DetailView):
    template_name = "supervisor/aluno_detalhe.html"
    context_object_name = "aluno"

    def get_queryset(self):
        return Student.objects.select_related("current_advisor")
