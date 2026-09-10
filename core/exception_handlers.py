from django.shortcuts import redirect

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
    
    #Chamado automaticamente pelo Django sempre que uma view levanta PermissionDenied (403), em qualquer app.
    
    if not request.user.is_authenticated:
        return redirect("login")

    home_url_name = HOME_BY_ROLE.get(request.user.role, "login")
    return redirect(home_url_name)