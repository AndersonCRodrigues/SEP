from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView, UpdateView
from django.urls import reverse_lazy
from .forms import AlunoCreationForm
from .models import Aluno
from core.utils import sincronizar_grupo
from core.mixins import GroupRequiredMixin


class HomeEstudanteView(LoginRequiredMixin, TemplateView):
    template_name = "student/home.html"


@login_required
def cadastrar_aluno(request):
    is_supervisor = request.user.groups.filter(name="Supervisor").exists() or request.user.is_superuser
    if not is_supervisor:
        raise PermissionDenied("Apenas Supervisores podem cadastrar Alunos.")

    if request.method == "POST":
        form = AlunoCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            sincronizar_grupo(user)
            messages.success(request, "Aluno cadastrado com sucesso!")
            return redirect("supervisor:painel")
    else:
        form = AlunoCreationForm()

    return render(request, "student/cadastro.html", {"form": form})


class PerfilAlunoView(GroupRequiredMixin, UpdateView):
    required_group = "Students"
    model = Aluno
    fields = [
        "nome_completo", "telefone",
        "logradouro", "numero", "complemento",
        "bairro", "cidade", "estado", "cep",
    ]
    template_name = "student/perfil.html"
    success_url = reverse_lazy("students:perfil")  # era student:perfil (sem "s")

    def get_object(self, queryset=None):
        return get_object_or_404(Aluno, pk=self.request.user.pk)


class MeuProfessorView(LoginRequiredMixin, TemplateView):
    template_name = "student/meu_professor.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aluno = get_object_or_404(Aluno, pk=self.request.user.pk)
        context["professor"] = aluno.orientador_atual
        return context