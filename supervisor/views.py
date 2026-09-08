from itertools import chain
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
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


def usuarios_alunos_e_professores():
    """
    Busca Alunos e Professores como suas subclasses reais (não CustomUser genérico),
    pra garantir que campos como crp/acting_area/matricula venham preenchidos.
    """
    alunos = Student.objects.filter(role=CustomUser.Role.ALUNO)
    professores = Teacher.objects.filter(
        role__in=[CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR]
    ).prefetch_related('acting_areas')
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
            user = form.save()
            sincronizar_grupo(user)
            messages.success(request, "Supervisor cadastrado com sucesso!")
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
