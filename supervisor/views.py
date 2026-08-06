from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.views.generic import ListView, TemplateView
from core.models import CustomUser
from core.mixins import GroupRequiredMixin
from core.forms import CustomUserCreationForm
from core.utils import sincronizar_grupo
from .utils import gerar_senha_temporaria, enviar_email_credenciais

# Importe a sua função sincronizar_grupo


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
        form = CustomUserCreationForm(request.POST, criado_por=request.user)
        if form.is_valid():
            # 1. Pausa o salvamento no banco para podermos manipular o objeto
            user = form.save(commit=False)
            
            # 2. Gera e criptografa a senha temporária
            senha_temporaria = gerar_senha_temporaria()
            user.set_password(senha_temporaria)
            
            # 3. Salva o usuário e os campos ManyToMany (necessário quando usamos commit=False)
            user.save()
            form.save_m2m() 
            
            # 4. Sincroniza os grupos baseados no cargo
            sincronizar_grupo(user)
            
            # 5. Verifica se é Paciente (US-5.1) e dispara o e-mail
            if user.role == CustomUser.Role.PACIENTE:
                enviar_email_credenciais(user, senha_temporaria)
                messages.success(request, f"Paciente {user.nome_completo} cadastrado e e-mail enviado com sucesso!")
            else:
                # Caso a view cadastre alunos/professores, você pode usar a mesma função
                enviar_email_credenciais(user, senha_temporaria)
                messages.success(request, f"Usuário {user.nome_completo} cadastrado com sucesso!")
                
            return redirect("supervisor:painel")
    else:
        form = CustomUserCreationForm(criado_por=request.user)

    return render(request, "supervisor/register.html", {"form": form})

    return render(request, "supervisor/register.html", {"form": form})