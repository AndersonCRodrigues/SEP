from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import ListView
from core.models import CustomUser


class GroupRequiredMixin(UserPassesTestMixin):
    required_group = "Supervisor"

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        return (
            self.request.user.groups.filter(name=self.required_group).exists() 
            or self.request.user.is_superuser
        )


class PainelSupervisorView(GroupRequiredMixin, ListView):
    model = CustomUser
    template_name = "painel_supervisor.html"  
    context_object_name = "usuarios_listados"

    def get_queryset(self):
        return CustomUser.objects.exclude(
            role__in=[CustomUser.Role.SUPERADMIN, CustomUser.Role.SUPERVISOR]
        )


class ListarUsuariosView(GroupRequiredMixin, ListView):
    model = CustomUser
    template_name = "listar_usuarios.html"  
    context_object_name = "usuarios_listados"

    def get_queryset(self):
        return CustomUser.objects.exclude(
            role__in=[CustomUser.Role.SUPERADMIN, CustomUser.Role.SUPERVISOR]
        )