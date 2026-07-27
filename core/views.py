from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.views.generic import ListView

from .forms import CustomUserCreationForm, LoginEmailOuMatriculaForm
from .models import CustomUser
from .decorators import role_required
from .mixins import RoleRequiredMixin


@login_required
def cadastrar_usuario(request):
    if request.user.role != CustomUser.Role.SUPERVISOR:
        raise PermissionDenied("Apenas Supervisor pode cadastrar usuários.")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST, criado_por=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Cadastro realizado com sucesso!")
            return redirect("listar_usuarios")
    else:
        form = CustomUserCreationForm(criado_por=request.user)

    return render(request, "cadastro.html", {"form": form})


@login_required
def area_usuario(request):
    return render(request, "area_usuario.html", {"usuario": request.user})


class CustomLoginView(LoginView):
    template_name = 'login.html'
    authentication_form = LoginEmailOuMatriculaForm

    def get_success_url(self):
        user = self.request.user
        destinos = {
            CustomUser.Role.SUPERVISOR: "painel_supervisor",
            CustomUser.Role.PROFESSOR: "painel_professor",
        }
        return reverse_lazy(destinos.get(user.role, "area_usuario"))


@role_required([CustomUser.Role.PROFESSOR])
def painel_professor(request):
    alunos = CustomUser.objects.filter(role=CustomUser.Role.ALUNO)
    return render(request, "painel_professor.html", {"alunos": alunos})


class PainelSupervisor(RoleRequiredMixin, ListView):
    model = CustomUser
    template_name = 'painel_supervisor.html'
    context_object_name = "usuarios_listados"
    allowed_roles = [CustomUser.Role.SUPERVISOR]

    def get_queryset(self):
        return CustomUser.objects.exclude(
            role__in=[CustomUser.Role.SUPERADMIN, CustomUser.Role.SUPERVISOR]
        )


class ListarUsuariosView(RoleRequiredMixin, ListView):
    model = CustomUser
    template_name = "listar_usuarios.html"
    context_object_name = "usuarios_listados"
    allowed_roles = [CustomUser.Role.SUPERVISOR]

    def get_queryset(self):
        return CustomUser.objects.exclude(
            role__in=[CustomUser.Role.SUPERADMIN, CustomUser.Role.SUPERVISOR]
        )