from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from core.mixins import GroupRequiredMixin
from supervisor.views.mocks import student_enrollment_fields
from core.utils import sincronizar_grupo

from ..forms import AlunoCreationForm
from ..models import Student
from .access import StudentOnly


class PainelEstudanteView(StudentOnly, TemplateView):
    template_name = "student/student_panel.html"


class PerfilAlunoView(GroupRequiredMixin, UpdateView):
    required_group = "Students"
    model = Student
    fields = [
        "first_name",
        "last_name",
        "telefone",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cidade",
        "estado",
        "cep",
    ]
    template_name = "student/perfil.html"
    success_url = reverse_lazy("students:home")

    def get_object(self, queryset=None):
        return get_object_or_404(Student, pk=self.request.user.pk)


class MeuProfessorView(StudentOnly, TemplateView):
    template_name = "student/meu_professor.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aluno = get_object_or_404(Student, pk=self.request.user.pk)
        context["professor"] = aluno.current_advisor
        return context


@login_required
def cadastrar_aluno(request):
    if not request.user.has_perm("students.add_student"):
        raise PermissionDenied("Apenas Coordenadores podem cadastrar Alunos.")

    if request.method == "POST":
        form = AlunoCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            sincronizar_grupo(user)
            messages.success(request, "Aluno cadastrado com sucesso!")
            return redirect("supervisor:painel")
    else:
        form = AlunoCreationForm()

    return render(
        request,
        "student/cadastro.html",
        {"form": form, "matricula_academica": student_enrollment_fields()},
    )
