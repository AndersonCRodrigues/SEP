from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.views.generic import ListView, TemplateView
from core.models import CustomUser
from core.mixins import GroupRequiredMixin
from core.forms import CustomUserCreationForm
from core.utils import sincronizar_grupo


class PainelSupervisorView(GroupRequiredMixin, ListView):
    required_group = "Supervisor"
    model = CustomUser
    template_name = "supervisor/supervisor_panel.html"
    context_object_name = "usuarios_listados"

    def get_queryset(self):
        return CustomUser.objects.exclude(
            role__in=[CustomUser.Role.SUPERADMIN, CustomUser.Role.SUPERVISOR]
        )


class ListarUsuariosView(GroupRequiredMixin, ListView):
    required_group = "Supervisor"
    model = CustomUser
    template_name = "supervisor/list_users.html"
    context_object_name = "usuarios_listados"

    def get_queryset(self):
        return CustomUser.objects.exclude(
            role__in=[CustomUser.Role.SUPERADMIN, CustomUser.Role.SUPERVISOR]
        )


class HomeSupervisorView(GroupRequiredMixin, TemplateView):
    required_group = "Supervisor"
    template_name = "supervisor/home_supervisor.html"


@login_required
def cadastrar_usuario(request):
    is_supervisor = (
        request.user.groups.filter(name="Supervisor").exists()
        or request.user.is_superuser
    )
    if not is_supervisor:
        raise PermissionDenied("Apenas Supervisores podem cadastrar novos usuários.")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST, created_by=request.user)
        if form.is_valid():
            user = form.save()
            sincronizar_grupo(user)
            messages.success(request, "Cadastro realizado com sucesso!")
            return redirect("supervisor:painel")
    else:
        form = CustomUserCreationForm(created_by=request.user)

    return render(request, "supervisor/register.html", {"form": form})