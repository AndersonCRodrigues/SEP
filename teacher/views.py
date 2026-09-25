from django.shortcuts import render, redirect, get_object_or_404
from students.models import Advising
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.views.generic import TemplateView, UpdateView
from django.urls import reverse_lazy
from .forms import ProfessorCreationForm, PerfilProfessorForm
from .models import Teacher
from core.utils import sincronizar_grupo
from django.core.exceptions import ValidationError
from core.models import CustomUser
from .forms import VincularAlunoForm
from students.models import StudentActivity
from .forms import StudentActivityForm
from students.models import CaseAssignment
from patient.models import ProgressNote
from django.utils import timezone
from django.utils.timesince import timesince


class HomeProfessorView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "teacher/home_teacher.html"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            from teacher.models import Teacher
            professor = Teacher.objects.get(pk=self.request.user.pk)
            context["alunos_orientados"] = professor.current_advisees.count()
        except Exception:
            context["alunos_orientados"] = 0
        return context


@login_required
def cadastrar_professor(request):
    if not request.user.has_perm("teacher.add_teacher"):
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


class PerfilProfessorView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Teacher
    form_class = PerfilProfessorForm
    template_name = "teacher/perfil.html"
    success_url = reverse_lazy("teacher:home")

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get_object(self, queryset=None):

        return get_object_or_404(Teacher, pk=self.request.user.pk)


class PainelProfessorView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "teacher/teacher_panel.html"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from students.models import Student

        professor = get_object_or_404(Teacher, pk=self.request.user.pk)

        if professor.role == CustomUser.Role.SUPERVISOR:
            context["alunos_vinculados"] = Student.objects.filter(
                current_advisor__isnull=False
            )
        else:
            context["alunos_vinculados"] = professor.current_advisees.all()

        context["alunos_disponiveis"] = Student.objects.filter(
            current_advisor__isnull=True
        )
        context["form_vincular"] = VincularAlunoForm()
        context["form_horas"] = StudentActivityForm(user=professor)
        return context


class ProntuariosProfessorView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "teacher/teacher_records.html"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        professor = get_object_or_404(Teacher, pk=self.request.user.pk)

        # Busca todos os casos abertos sob orientação deste professor
        casos_qs = (
            CaseAssignment.objects.open()
            .filter(student__current_advisor=professor)
            .select_related("patient", "student")
            .order_by("-start_date")
        )

        # Enriquece cada caso com a última evolução e se está pendente de revisão
        casos_enriquecidos = []
        for caso in casos_qs:
            ultima_nota = (
                ProgressNote.objects
                .filter(patient=caso.patient, student=caso.student)
                .order_by("-updated_at")
                .first()
            )
            caso.ultima_evolucao = (
                timesince(ultima_nota.updated_at) + " atrás"
                if ultima_nota else None
            )
            caso.pendente_revisao = (
                ultima_nota.pending_confirmation if ultima_nota else False
            )
            casos_enriquecidos.append(caso)

        context["casos"] = casos_enriquecidos
        return context


class PresencaProfessorView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "teacher/teacher_presence.html"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )


class AreaAtuacaoProfessorView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "teacher/teacher_area.html"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )


@login_required
def vincular_aluno(request):
    is_authorized = request.user.role in (
        CustomUser.Role.PROFESSOR,
        CustomUser.Role.SUPERVISOR,
    )
    if not is_authorized:
        raise PermissionDenied(
            "Apenas Professores e Supervisores podem vincular Alunos."
        )

    professor = get_object_or_404(Teacher, pk=request.user.pk)

    if request.method == "POST":
        form = VincularAlunoForm(request.POST)
        if form.is_valid():
            aluno = form.cleaned_data["aluno"]
            periodo = form.cleaned_data["periodo"]
            try:
                Advising.objects.change_advisor(aluno, professor, term=periodo)
                messages.success(
                    request, f"{aluno.get_full_name()} vinculado com sucesso!"
                )
            except ValidationError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Corrija os erros do formulário de vínculo.")

    return redirect("teacher:painel")


@login_required
def lancar_horas(request):
    is_authorized = request.user.role in (
        CustomUser.Role.PROFESSOR,
        CustomUser.Role.SUPERVISOR,
    )
    if not is_authorized:
        raise PermissionDenied("Apenas Professores e Supervisores podem lançar horas.")

    if request.method == "POST":
        professor = get_object_or_404(Teacher, pk=request.user.pk)
        form = StudentActivityForm(request.POST, user=professor)
        if form.is_valid():
            student = form.cleaned_data["student"]

            if not StudentActivity.can_be_created_by(request.user, student=student):
                raise PermissionDenied("Este aluno não está sob sua orientação ativa.")

            form.save()
            messages.success(request, "Horas registradas com sucesso.")
        else:
            messages.error(request, "Corrija os erros do formulário de horas.")

    return redirect("teacher:painel")

class TeacherAssignTriageView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "teacher/teacher_assign_triage.html"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )
