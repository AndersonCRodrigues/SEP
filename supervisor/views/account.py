from itertools import chain

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView

from core.mixins import GroupRequiredMixin
from core.models import CustomUser
from core.notifications import enviar_credenciais_por_telefone
from core.utils import sincronizar_grupo
from students.models import Student
from teacher.forms import PerfilProfessorForm
from teacher.models import Teacher

from ..forms import SupervisorCreationForm
from ..utils import enviar_email_credenciais, gerar_senha_temporaria


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


@login_required
def cadastrar_supervisor(request):
    if not request.user.has_perm("core.add_customuser"):
        raise PermissionDenied("Apenas o Superadmin pode cadastrar Coordenador.")

    if request.method == "POST":
        form = SupervisorCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)

            senha_temporaria = gerar_senha_temporaria()
            user.set_password(senha_temporaria)
            user.must_change_password = True

            user.save()
            form.save_m2m()

            sincronizar_grupo(user)

            email_ok = enviar_email_credenciais(user, senha_temporaria)
            telefone_ok = enviar_credenciais_por_telefone(user, senha_temporaria)

            if email_ok and telefone_ok:
                messages.success(
                    request,
                    f"Coordenador {user.get_full_name()} cadastrado e credenciais "
                    "enviadas com sucesso!",
                )
            else:
                messages.warning(
                    request,
                    f"Coordenador {user.get_full_name()} cadastrado, mas houve falha ao "
                    "enviar as credenciais. Verifique o log de auditoria e informe a senha "
                    "manualmente se necessario.",
                )
            return redirect("superadmin:home")
    else:
        form = SupervisorCreationForm()

    return render(request, "supervisor/cadastro_supervisor.html", {"form": form})
