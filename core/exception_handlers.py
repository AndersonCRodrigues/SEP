from django.contrib import messages
from django.shortcuts import redirect,render
from django.urls import resolve
from http import HTTPStatus

from core.models import CustomUser

Role = CustomUser.Role

HOME_BY_ROLE = {
    Role.ALUNO: "students:home",
    Role.PROFESSOR: "teacher:home",
    Role.SUPERVISOR: "supervisor:home",
    Role.ADMINISTRATIVO: "administration:home",
    Role.SUPERADMIN: "superadmin:home",
    Role.PACIENTE: "patient:home",
}


def custom_permission_denied_view(request, exception):
    if not request.user.is_authenticated:
        messages.error(request, "Sua sessão expirou. Entre novamente para continuar.")
        return redirect("login")

    detalhe = next((str(arg) for arg in getattr(exception, "args", ()) if arg), "")
    messages.error(request, detalhe or "Você não tem acesso a essa página.")

    if request.user.is_superuser:
        return redirect("superadmin:home")

    home_url_name = HOME_BY_ROLE.get(request.user.role, "login")
    return redirect(home_url_name)



def csrfail(request,reason=''):
    referer=request.META.get("HTTP_REFERER","/")
    if resolve(request.path).url_name=="login":
        if request.user.is_authenticated:
            return redirect("home_redirect")
        return redirect("login")
    return render(request,"crsfail.html",context={"referer":referer},status=HTTPStatus.FORBIDDEN)
