from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from core.mixins import GroupRequiredMixin
from .forms import AdministrativoCreationForm
from core.utils import sincronizar_grupo
from core.models import CustomUser
from .forms import AdministrativoCreationForm
from patient.forms import PacienteCreationForm
from django.contrib.auth.mixins import PermissionRequiredMixin


@login_required
def cadastrar_paciente(request):
    if not request.user.has_perm("core.add_customuser"):
        raise PermissionDenied("Você não tem permissão para cadastrar Paciente.")
    is_administrativo = request.user.is_superuser or request.user.role == CustomUser.Role.ADMINISTRATIVO
    if not is_administrativo:
        raise PermissionDenied("Apenas o Administrativo pode cadastrar Paciente.")

    if request.method == "POST":
        form = PacienteCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            sincronizar_grupo(user)
            messages.success(request, "Paciente cadastrado com sucesso!")
            return redirect("administration:home")
    else:
        form = PacienteCreationForm()

    return render(request, "administration/cadastrar_paciente.html", {"form": form})


class PainelAdministracaoView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "administration/administration_panel.html"

    def test_func(self):
        return self.request.user.has_perm("core.view_customuser")


class PerfilAdministrativoView(PermissionRequiredMixin, UpdateView):
    permission_required = "core.view_customuser"
    model = CustomUser
    fields = [...]
    template_name = "administration/perfil.html"
    success_url = reverse_lazy("administration:perfil")

    def get_object(self, queryset=None):
        return self.request.user


@login_required
def cadastrar_administrativo(request):
    if not request.user.is_superuser:
        raise PermissionDenied("Apenas o Superadmin pode cadastrar Administrativo.")

    if request.method == "POST":
        form = AdministrativoCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            sincronizar_grupo(user)
            messages.success(request, "Administrativo cadastrado com sucesso!")
            return redirect("superadmin:painel")  
    else:
        form = AdministrativoCreationForm()

    return render(request, "administration/cadastro.html", {"form": form})