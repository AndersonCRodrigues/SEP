from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from core.models import CustomUser
from .forms import LoginEmailOuMatriculaForm


class RedirecionarHomeView(LoginRequiredMixin, View):
    ROLE_URL_MAP = {
        CustomUser.Role.SUPERADMIN: "superadmin:home",
        CustomUser.Role.SUPERVISOR: "supervisor:home",
        CustomUser.Role.PROFESSOR: "teacher:home",
        CustomUser.Role.ALUNO: "students:home",
        CustomUser.Role.ADMINISTRATIVO: "administration:home",
        CustomUser.Role.PACIENTE: "patient:home",
    }

    def get(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return redirect("superadmin:home")

        url_name = self.ROLE_URL_MAP.get(request.user.role)
        if url_name is None:
            return redirect("login")

        return redirect(url_name)


class CustomLoginView(LoginView):
    template_name = "login.html"
    authentication_form = LoginEmailOuMatriculaForm

    def get_success_url(self):
        return reverse_lazy("home_redirect")


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("login")