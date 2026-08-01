from django.views.generic import ListView, TemplateView
from core.models import CustomUser
from core.mixins import GroupRequiredMixin


class PainelProfessorView(GroupRequiredMixin, ListView):
    required_group = "Professors"
    model = CustomUser
    template_name = "teacher/teacher_panel.html"
    context_object_name = "alunos"

    def get_queryset(self):
        return CustomUser.objects.filter(role=CustomUser.Role.ALUNO)


class HomeProfessorView(GroupRequiredMixin, TemplateView):
    required_group = "Professors"
    template_name = "teacher/home_teacher.html"