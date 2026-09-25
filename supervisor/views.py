from itertools import chain

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from areas.forms import AreaAtuacaoForm
from areas.models import AreaActing
from core.constants import TriageStatus
from core.mixins import GroupRequiredMixin
from core.models import CustomUser
from core.utils import sincronizar_grupo
from students.models import Student
from teacher.forms import PerfilProfessorForm, StudentActivityForm, VincularAlunoForm
from teacher.models import Teacher
from triage.models import Referral, TriageRecord

from .forms import SupervisorCreationForm
from .utils import enviar_email_credenciais, gerar_senha_temporaria


def usuarios_alunos_e_professores():
    """
    Busca Alunos e Professores como suas subclasses reais (não CustomUser genérico),
    pra garantir que campos como crp/acting_area/matricula venham preenchidos.
    """
    alunos = Student.objects.filter(role=CustomUser.Role.ALUNO)
    professores = Teacher.objects.filter(
        role__in=[CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR]
    ).prefetch_related("acting_areas")
    return sorted(chain(alunos, professores), key=lambda u: u.get_full_name())


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
                f"Supervisor {user.get_full_name()} cadastrado e e-mail enviado com sucesso!",
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


class PainelOrientacaoSupervisorView(GroupRequiredMixin, TemplateView):
    """
    Painel de orientação/encaminhamentos do Supervisor — separado do
    PainelProfessorView (que é só-Professor) porque o Supervisor tem
    acesso geral (todos os alunos vinculados, todas as triagens pendentes,
    histórico completo, todos os encaminhamentos).
    """

    required_group = "Supervisor"
    template_name = "supervisor/orientacao_panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supervisor = get_object_or_404(Teacher, pk=self.request.user.pk)

        context["alunos_vinculados"] = Student.objects.filter(
            current_advisor__isnull=False
        )
        context["alunos_disponiveis"] = Student.objects.filter(
            current_advisor__isnull=True
        )
        # Triagens já submetidas pelo Aluno, esperando parecer/encaminhamento.
        context["triagens_pendentes"] = TriageRecord.objects.visible_to(
            self.request.user
        ).filter(status=TriageStatus.SUBMITTED)
        # Histórico: triagens que já saíram do "aguardando parecer" — já
        # encaminhadas ou já fechadas.
        context["historico_triagens"] = (
            TriageRecord.objects.visible_to(self.request.user)
            .exclude(status__in=[TriageStatus.OPEN, TriageStatus.SUBMITTED])
            .order_by("-created_at")
        )
        context["todos_encaminhamentos"] = Referral.objects.visible_to(
            self.request.user
        )
        context["form_vincular"] = VincularAlunoForm()
        context["form_horas"] = StudentActivityForm(user=supervisor)
        return context


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
