from itertools import chain
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView, CreateView, UpdateView
from core.models import CustomUser
from teacher.models import Professor
from students.models import Aluno
from areas.models import AreaActing
from .forms import SupervisorCreationForm
from areas.forms import AreaAtuacaoForm
from core.utils import sincronizar_grupo
from django.contrib.auth.mixins import PermissionRequiredMixin


def usuarios_alunos_e_professores():
  
    alunos = Aluno.objects.filter(role=CustomUser.Role.ALUNO)
    professores = Professor.objects.filter(role__in=[CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR])
    return sorted(chain(alunos, professores), key=lambda u: u.nome_completo)


class PainelSupervisorView(PermissionRequiredMixin, ListView):
    permission_required = "teacher.view_professor"
    template_name = "supervisor/supervisor_panel.html"
    context_object_name = "usuarios_listados"

    def get_queryset(self):
        return usuarios_alunos_e_professores()


class ListarUsuariosView(PermissionRequiredMixin, ListView):
    permission_required = "teacher.view_professor"
    template_name = "supervisor/list_users.html"
    context_object_name = "usuarios_listados"

    def get_queryset(self):
        return usuarios_alunos_e_professores()


class HomeSupervisorView(PermissionRequiredMixin, TemplateView):
    permission_required = "teacher.view_professor"
    template_name = "supervisor/home_supervisor.html"


class ListaAreasView(PermissionRequiredMixin, ListView):
    permission_required = "areas.view_areaacting"
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


@login_required
def cadastrar_supervisor(request):
    if not request.user.is_superuser:
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