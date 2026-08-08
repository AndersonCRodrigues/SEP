from django.shortcuts import render, redirect, get_object_or_404
from students.models import Orientacao  
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin,UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView, UpdateView
from django.urls import reverse_lazy
from .forms import ProfessorCreationForm, PerfilProfessorForm
from .models import Professor
from core.utils import sincronizar_grupo
from django.core.exceptions import ValidationError
from core.models import CustomUser
from .forms import VincularAlunoForm



class HomeProfessorView(LoginRequiredMixin, TemplateView):
    template_name = "teacher/home_teacher.html"


@login_required
def cadastrar_professor(request):
    is_supervisor = (
        request.user.groups.filter(name="Supervisor").exists()
        or request.user.is_superuser
    )
    if not is_supervisor:
        raise PermissionDenied("Apenas Supervisores podem cadastrar Professores.")

    if request.method == "POST":
        form = ProfessorCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            sincronizar_grupo(user)
            messages.success(request, "Professor cadastrado com sucesso!")
            return redirect("supervisor:painel")
    else:
        form = ProfessorCreationForm()

    return render(request, "teacher/cadastro.html", {"form": form})


class PerfilProfessorView(LoginRequiredMixin, UpdateView):
    model = Professor
    form_class = PerfilProfessorForm
    template_name = "teacher/perfil.html"
    success_url = reverse_lazy("teacher:home") 

    def get_object(self, queryset=None):
        
        return get_object_or_404(Professor, pk=self.request.user.pk)
    



class PainelProfessorView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "teacher/teacher_panel.html"

    def test_func(self):
        return self.request.user.role in (CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from students.models import Aluno

        professor = get_object_or_404(Professor, pk=self.request.user.pk)
        context["alunos_vinculados"] = professor.orientandos_atuais.all()
        context["alunos_disponiveis"] = Aluno.objects.filter(orientador_atual__isnull=True)
        context["form_vincular"] = VincularAlunoForm()
        return context


@login_required
def vincular_aluno(request):

    is_professor = request.user.role in (CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR)
    if not is_professor:
        raise PermissionDenied("Apenas Professores podem vincular Alunos.")

    professor = get_object_or_404(Professor, pk=request.user.pk)

    if request.method == "POST":
        form = VincularAlunoForm(request.POST)
        if form.is_valid():
            aluno = form.cleaned_data["aluno"]
            periodo = form.cleaned_data["periodo"]
            try:
                Orientacao.objects.trocar_orientador(aluno=aluno, novo_professor=professor, periodo=periodo)
                messages.success(request, f"{aluno.nome_completo} vinculado com sucesso!")
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Corrija os erros do formulário de vínculo.")

    return redirect("teacher:painel")