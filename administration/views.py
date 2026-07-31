from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import ListView
from core.models import CustomUser


class GroupRequiredMixin(UserPassesTestMixin):
    required_group = "Administration"

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        return (
            self.request.user.groups.filter(name=self.required_group).exists() 
            or self.request.user.is_superuser
        )


class PainelAdministracaoView(GroupRequiredMixin, ListView):
    model = CustomUser
    template_name = "painel_administracao.html"  
    context_object_name = "atendimentos_ou_usuarios"

    def get_queryset(self):
        return CustomUser.objects.filter(
            role__in=[CustomUser.Role.ALUNO, CustomUser.Role.PROFESSOR]
        )