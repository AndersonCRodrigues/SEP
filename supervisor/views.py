from itertools import chain
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect,get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView, TemplateView, CreateView, UpdateView
from core.models import CustomUser
from core.mixins import GroupRequiredMixin
from teacher.models import Teacher
from students.models import Student
from areas.models import AreaActing
from .forms import SupervisorCreationForm
from areas.forms import AreaAtuacaoForm
from core.utils import sincronizar_grupo
from .utils import gerar_senha_temporaria, enviar_email_credenciais
from teacher.forms import PerfilProfessorForm


def usuarios_alunos_e_professores():
    """
    Busca Alunos e Professores como suas subclasses reais (não CustomUser genérico),
    pra garantir que campos como crp/acting_area/matricula venham preenchidos.
    """
    alunos = Student.objects.filter(role=CustomUser.Role.ALUNO)
    professores = Teacher.objects.filter(
        role__in=[CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR]
    ).prefetch_related("acting_areas")
    return sorted(chain(alunos, professores), key=lambda u: u.nome_completo)


class PainelSupervisorView(GroupRequiredMixin, ListView):
    required_group = "Supervisor"
    template_name = "supervisor/supervisor_panel.html"
    context_object_name = "usuarios_listados"

    def get_queryset(self):
        return usuarios_alunos_e_professores()


class ListarUsuariosView(GroupRequiredMixin, ListView):
    required_group = "Supervisor"
    template_name = "supervisor/list_users.html"
    context_object_name = "usuarios_listados"

    def get_queryset(self):
        return usuarios_alunos_e_professores()


class HomeSupervisorView(GroupRequiredMixin, TemplateView):
    required_group = "Supervisor"
    template_name = "supervisor/home_supervisor.html"


@login_required
def cadastrar_supervisor(request):
    if not request.user.has_perm("core.add_customuser"):
        raise PermissionDenied("Apenas o Superadmin pode cadastrar Supervisor.")

    if request.method == "POST":
        form = SupervisorCreationForm(request.POST)
        if form.is_valid():
            # 1. Pausa o salvamento no banco para gerarmos a senha
            user = form.save(commit=False)

            # 2. Gera e criptografa a senha temporária
            senha_temporaria = gerar_senha_temporaria()
            user.set_password(senha_temporaria)

            # 3. Salva o usuário e os campos ManyToMany do formulário
            user.save()
            form.save_m2m()

            # 4. Sincroniza os grupos
            sincronizar_grupo(user)

            # 5. Dispara o e-mail com as credenciais
            enviar_email_credenciais(user, senha_temporaria)

            messages.success(
                request,
                f"Supervisor {user.nome_completo} cadastrado e e-mail enviado com sucesso!",
            )
            return redirect("superadmin:painel")
    else:
        form = SupervisorCreationForm()

    return render(request, "supervisor/cadastro_supervisor.html", {"form": form})


class ListaAreasView(GroupRequiredMixin, ListView):
    required_group = "Supervisor"
    model = AreaActing
    template_name = "supervisor/area_list.html"
    context_object_name = "areas"


class CriarAreaView(PermissionRequiredMixin, CreateView):
    permission_required = "areas.add_areaacting"
    model = AreaActing
    form_class = AreaAtuacaoForm
    template_name = "supervisor/area_form.html"
    success_url = reverse_lazy("supervisor:areas")


class EditarAreaView(PermissionRequiredMixin, UpdateView):
    permission_required = "areas.change_areaacting"
    model = AreaActing
    form_class = AreaAtuacaoForm
    template_name = "supervisor/area_form.html"
    success_url = reverse_lazy("supervisor:areas")


class PerfilSupervisorView(GroupRequiredMixin, UpdateView):
    required_group = "Supervisor"
    model = Teacher
    form_class = PerfilProfessorForm
    template_name = "supervisor/perfil.html"
    success_url = reverse_lazy("supervisor:home")

    def get_object(self, queryset=None):
        user = self.request.user
        
        try:
            return Teacher.objects.get(pk=user.pk)
        except Teacher.DoesNotExist:
            teacher = Teacher(customuser_ptr_id=user.pk)
            teacher.__dict__.update(user.__dict__)
            teacher.role = CustomUser.Role.SUPERVISOR
            teacher.save()
            return teacher

    def form_valid(self, form):
        messages.success(self.request, "Perfil atualizado com sucesso!")
        return super().form_valid(form)