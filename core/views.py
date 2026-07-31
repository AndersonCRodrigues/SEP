from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from .utils import sincronizar_grupo

from .forms import CustomUserCreationForm, LoginEmailOuMatriculaForm



@login_required
def home(request):
    user_groups = list(request.user.groups.values_list('name', flat=True))
    return render(request, "home.html", {
        "usuario": request.user,
        "user_groups": user_groups,
    })


@login_required
def cadastrar_usuario(request):
    is_supervisor = (
        request.user.groups.filter(name="Supervisor").exists()
        or request.user.is_superuser
    )

    if not is_supervisor:
        raise PermissionDenied("Apenas Supervisores podem cadastrar novos usuários.")

    if request.method == "POST":
        form = CustomUserCreationForm(request.POST, criado_por=request.user)
        if form.is_valid():
            user = form.save()
            sincronizar_grupo(user)
            messages.success(request, "Cadastro realizado com sucesso!")
            return redirect("supervisor:painel")
    else:
        form = CustomUserCreationForm(criado_por=request.user)

    return render(request, "cadastro.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = 'login.html'
    authentication_form = LoginEmailOuMatriculaForm

    def get_success_url(self):
        return reverse_lazy("home")


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("login")


@login_required
def area_usuario(request):
    return render(request, "area_usuario.html", {"usuario": request.user})