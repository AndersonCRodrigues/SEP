from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import ListView
from core.models import CustomUser


class GroupRequiredMixin(UserPassesTestMixin):
    required_group = "Professors"

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        return (
            self.request.user.groups.filter(name=self.required_group).exists() 
            or self.request.user.is_superuser
        )


class PainelProfessorView(GroupRequiredMixin, ListView):
    model = CustomUser
    template_name = "painel_professor.html"  # Nome exato da sua pasta templates
    context_object_name = "alunos"

    def get_queryset(self):
        return CustomUser.objects.filter(role=CustomUser.Role.ALUNO)