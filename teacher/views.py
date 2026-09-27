from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView, TemplateView, UpdateView

from core.models import CustomUser
from core.month_calendar import displayed_month, month_calendar, month_range
from core.utils import sincronizar_grupo
from patient.models import Patient

from patient.models import ProgressNote
from students.models import (
    Advising,
    CaseAssignment,
    Student,
    StudentActivity,
    advisees_visible_to,
)

from .forms import (
    PerfilProfessorForm,
    PerformanceReviewForm,
    ProfessorCreationForm,
    StudentActivityForm,
    VincularAlunoForm,
)
from .models import Teacher


class HomeProfessorView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "teacher/home_teacher.html"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def _montar_calendario(self, hoje):
        """Mês navegável via ?mes=&ano= (sem JS). Só marca dias com
        Appointment real (status Agendado) -- "Disponível"/"Pendente" do
        Figma não têm equivalente no backend ainda, então ficam de fora até
        virarem task."""
        from datetime import datetime, time

        from scheduling.models import Appointment

        ano, mes = displayed_month(self.request.GET, hoje)
        primeiro, ultimo = month_range(ano, mes)

        # `scheduled_at` é guardado em UTC e o mês exibido é o local: filtrar
        # pelos componentes de data do campo joga agendamento da virada do mês
        # para o mês errado. Por isso o recorte é um intervalo timezone-aware.
        inicio = timezone.make_aware(datetime.combine(primeiro, time.min))
        fim = timezone.make_aware(datetime.combine(ultimo, time.max))

        agendamentos_mes = Appointment.objects.visible_to(self.request.user).filter(
            scheduled_at__gte=inicio,
            scheduled_at__lte=fim,
            status=Appointment.Status.SCHEDULED,
        )
        dias_com_agendamento = {
            timezone.localtime(momento).date()
            for momento in agendamentos_mes.values_list("scheduled_at", flat=True)
        }

        return month_calendar(ano, mes, hoje, dias_com_agendamento)

    def get_context_data(self, **kwargs):
        from students.models import Attendance

        context = super().get_context_data(**kwargs)
        alunos = advisees_visible_to(self.request.user)

        hoje = timezone.localdate()
        context.update(self._montar_calendario(hoje))

        orientados = alunos.count()
        presentes = Attendance.objects.filter(student__in=alunos, date=hoje).count()
        evolucoes_pendentes = ProgressNote.objects.visible_to(self.request.user).filter(
            confirmed_at__isnull=True
        )

        context["indicators"] = [
            {"label": "Alunos orientados", "value": orientados},
            {
                "label": "Pacientes ativos",
                "value": Patient.objects.visible_to(self.request.user)
                .filter(flow_status=Patient.FlowStatus.IN_TREATMENT)
                .count(),
            },
            {"label": "Presença hoje", "value": f"{presentes}/{orientados}"},
            {"label": "Avaliações pendentes", "value": evolucoes_pendentes.count()},
        ]

        atividades = []
        for nota in evolucoes_pendentes.select_related("patient", "student").order_by(
            "-created_at"
        )[:5]:
            atividades.append(
                {
                    "kind": "record",
                    "section": "Prontuário",
                    "title": f"Evolução de {nota.patient.nome_completo}",
                    "detail": f"Aluno responsável: {nota.student.nome_completo}",
                    "label": "Revisar",
                    "level": "warning",
                    "url": reverse("teacher:prontuario_detalhe", args=[nota.pk]),
                    "link_label": "Ver prontuário",
                    "when": nota.created_at,
                }
            )

        for paciente in (
            Patient.objects.visible_to(self.request.user)
            .filter(flow_status=Patient.FlowStatus.REFERRED)
            .order_by("-created_at")[:5]
        ):
            atividades.append(
                {
                    "kind": "triage",
                    "section": "Encaminhamento",
                    "title": f"Encaminhamento — {paciente.get_full_name()}",
                    "detail": "Aguardando definição de aluno responsável",
                    "label": "Encaminhar",
                    "level": "danger",
                    "url": reverse("teacher:encaminhar", args=[paciente.pk]),
                    "link_label": "Encaminhar para aluno",
                    "when": paciente.created_at,
                }
            )

        atividades.sort(key=lambda item: item["when"], reverse=True)
        context["activities"] = atividades[:5]
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



def _painel_redirect_for(user):
    if user.role == CustomUser.Role.SUPERVISOR:
        return "supervisor:orientacao"
    return "teacher:home"


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

    return redirect(_painel_redirect_for(request.user))


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

    return redirect(_painel_redirect_for(request.user))


# ---------------------------------------------------------------------------
# Card: Alunos sob orientação
# ---------------------------------------------------------------------------


class AlunosOrientacaoView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = "teacher/aluno_lista.html"
    context_object_name = "alunos"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get_queryset(self):
        from students.models import Student

        alunos = advisees_visible_to(self.request.user)

        termo_busca = self.request.GET.get("q", "").strip()
        if termo_busca:
            # nome_completo é uma @property em CustomUser (get_full_name()),
            # não uma coluna -- não dá pra usar num filter()/Q(). Busca-se
            # pelos campos reais (first_name/last_name) em vez disso.
            alunos = alunos.filter(
                Q(first_name__icontains=termo_busca)
                | Q(last_name__icontains=termo_busca)
                | Q(matricula__icontains=termo_busca)
            )

        fase_filtro = self.request.GET.get("fase", "")
        if fase_filtro in Student.Stage.values:
            alunos = alunos.filter(stage=fase_filtro)

        return alunos.order_by("first_name", "last_name")

    def get_context_data(self, **kwargs):
        from students.models import Student

        context = super().get_context_data(**kwargs)
        context["termo_busca"] = self.request.GET.get("q", "").strip()
        context["fase_filtro"] = self.request.GET.get("fase", "")
        context["fases_disponiveis"] = Student.Stage.choices
        return context


class AlunoDetalheView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    template_name = "teacher/aluno_detalhe.html"
    context_object_name = "aluno"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get_queryset(self):
        from students.models import Student

        return Student.objects.all()

    def get_object(self, queryset=None):
        from students.models import can_reach_student

        aluno = super().get_object(queryset)
        if not can_reach_student(self.request.user, aluno):
            raise PermissionDenied("Este aluno não está sob sua orientação.")
        return aluno

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aluno = context["aluno"]
        context["casos_abertos"] = aluno.open_cases.select_related(
            "patient", "acting_area"
        )
        context["casos_encerrados"] = aluno.case_history.filter(
            end_date__isnull=False
        ).select_related("patient")
        context["feedbacks"] = student_feedbacks(self.request.user, aluno)
        return context


# ---------------------------------------------------------------------------
# Card: Prontuários
# ---------------------------------------------------------------------------


class ProntuariosView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "teacher/prontuarios_lista.html"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)
        notas = (
            ProgressNote.objects.visible_to(self.request.user)
            .select_related("patient", "student")
            .order_by("-created_at")
        )

        termo_busca = self.request.GET.get("q", "").strip()
        if termo_busca:
            # Idem: nome_completo não existe como coluna em Patient/Student
            # (é property herdada de CustomUser), então o filtro por nome
            # precisa ir direto em first_name/last_name.
            notas = notas.filter(
                Q(patient__first_name__icontains=termo_busca)
                | Q(patient__last_name__icontains=termo_busca)
                | Q(student__first_name__icontains=termo_busca)
                | Q(student__last_name__icontains=termo_busca)
            )

        # MOCK: ainda não existe regra de prazo/SLA para "Pendente" vs "Revisar"
        # no backend. Por ora só refletimos pending_confirmation (o que já
        # existe) e usamos o índice pra variar o badge na tela. Quando a regra
        # de prazo for definida como task, trocar por ela aqui.
        context["linhas"] = [
            {
                "nota": nota,
                "atrasada": nota.pending_confirmation and indice % 2 == 0,
            }
            for indice, nota in enumerate(notas)
        ]
        context["termo_busca"] = termo_busca
        return context


class ProntuarioDetalheView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Detalhe de uma evolução + confirmação.

    BLOQUEADA por enquanto (pedido de 19/09): a tela inteira ainda é MOCK
    -- `pode_confirmar` é sempre True em get_context_data() e o post()
    não persiste nada de verdade (ver lógica real comentada mais abaixo,
    dentro do post()). Como não existe fluxo de confirmação de verdade
    por trás, fechamos o acesso à página aqui em cima, via get()/post(),
    em vez de deixar entrar e simular sucesso -- assim ninguém confirma
    uma evolução "de mentirinha" achando que é de verdade, seja entrando
    pela lista de Prontuários, pelo card de Atividades recentes da Home,
    ou digitando a URL direto.

    Reverter: apagar o get() abaixo e trocar o post() por só a lógica
    real (hoje comentada no fim do método) quando o fluxo de confirmação
    for fechado e validado com produto.
    """

    template_name = "teacher/prontuario_detalhe.html"
    context_object_name = "nota"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get(self, request, *args, **kwargs):
        messages.info(
            request,
            "O detalhe do prontuário ainda está em construção e não pode "
            "ser acessado no momento.",
        )
        return redirect("teacher:prontuarios")

    def get_queryset(self):

        return ProgressNote.objects.visible_to(self.request.user).select_related(
            "patient", "student"
        )

    def get_context_data(self, **kwargs):
        # MOCK (a pedido do front, validação de 12/09): o botão de confirmar
        # ainda não tem o fluxo fechado com produto, então aparece sempre
        # habilitado aqui. A checagem real (editable_fields_for) está
        # comentada no post() abaixo, pronta pra voltar quando o fluxo for
        # validado. Mantido só para quando o bloqueio do get() acima for
        # removido -- hoje esta tela nem chega a renderizar.
        context = super().get_context_data(**kwargs)
        context["pode_confirmar"] = True
        return context

    def post(self, request, *args, **kwargs):
        messages.info(
            request,
            "O detalhe do prontuário ainda está em construção e não pode "
            "ser acessado no momento.",
        )
        return redirect("teacher:prontuarios")

        # --- mock anterior (a pedido do front, validação de 12/09): não
        # persistia nada, só simulava sucesso pra validar o clique. Deixado
        # comentado junto com o bloqueio de acesso -- não faz sentido
        # simular confirmação de uma tela que está fechada.
        # self.get_object()
        # messages.success(request, "Evolução confirmada (simulado).")
        # return redirect("teacher:prontuarios")

        # --- lógica real, comentada até o fluxo ser validado com produto ---
        # nota = self.get_object()
        # if "confirmed_by" not in nota.editable_fields_for(request.user):
        #     raise PermissionDenied("Você não pode confirmar esta evolução.")
        # nota.confirmed_by = request.user
        # nota.confirmed_at = timezone.now()
        # nota.save(update_fields=["confirmed_by", "confirmed_at"])
        # messages.success(request, "Evolução confirmada com sucesso.")
        # return redirect("teacher:prontuarios")


# ---------------------------------------------------------------------------
# Card: Presença
# ---------------------------------------------------------------------------


def advisees_by_name(user, search):
    students = advisees_visible_to(user).order_by("first_name", "last_name")
    if search:
        students = students.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search)
        )
    return students


def student_feedbacks(user, student):
    from students.models import PerformanceReview

    return (
        PerformanceReview.objects.visible_to(user)
        .filter(student=student)
        .select_related("teacher")
        .order_by("-updated_at")
    )


class PresencaView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "teacher/presenca.html"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get_context_data(self, **kwargs):
        from students.models import Attendance

        context = super().get_context_data(**kwargs)
        search = self.request.GET.get("q", "").strip()
        students = advisees_by_name(self.request.user, search)

        today = timezone.localdate()
        attendance_today = {
            record.student_id: record
            for record in Attendance.objects.filter(student__in=students, date=today)
        }

        context["rows"] = [
            {"student": student, "attendance": attendance_today.get(student.pk)}
            for student in students
        ]
        context["today"] = today
        context["search"] = search
        return context


# ---------------------------------------------------------------------------
# Card: Avaliações
# ---------------------------------------------------------------------------


class AvaliacoesView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "teacher/avaliacoes.html"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search = self.request.GET.get("q", "").strip()
        students = advisees_by_name(self.request.user, search)

        student_id = self.request.GET.get("aluno", "").strip()
        chosen = (
            students.filter(pk=student_id).first() if student_id.isdigit() else None
        )

        context["students"] = students
        context["search"] = search

        if chosen:
            context["chosen"] = chosen
            context["form_feedback"] = PerformanceReviewForm()
            context["feedbacks"] = student_feedbacks(self.request.user, chosen)

        return context


@login_required
def marcar_presenca(request, aluno_id):
    from students.models import Attendance, Student

    aluno = get_object_or_404(Student, pk=aluno_id)

    if not Attendance.can_be_created_by(request.user, student=aluno):
        raise PermissionDenied("Este aluno não está sob sua orientação.")

    if request.method == "POST":
        hoje = timezone.localdate()
        _registro, criado = Attendance.objects.get_or_create(
            student=aluno,
            date=hoje,
            defaults={"registered_by": request.user},
        )
        if criado:
            messages.success(request, f"Presença de {aluno.nome_completo} registrada.")
        else:
            messages.info(request, f"{aluno.nome_completo} já estava presente hoje.")

    return redirect("teacher:presenca")


@login_required
def registrar_feedback(request, aluno_id):
    from students.models import PerformanceReview, Student

    professor = get_object_or_404(Teacher, pk=request.user.pk)
    aluno = get_object_or_404(Student, pk=aluno_id)

    if not PerformanceReview.can_be_created_by(request.user, student=aluno):
        raise PermissionDenied("Você não pode avaliar este aluno.")

    if request.method == "POST":
        form = PerformanceReviewForm(request.POST)
        if form.is_valid():
            avaliacao = form.save(commit=False)
            avaliacao.student = aluno
            avaliacao.teacher = professor
            avaliacao.save()
            messages.success(request, "Feedback registrado com sucesso.")
        else:
            messages.error(request, "Corrija os erros do formulário de feedback.")

    return redirect(f"{reverse('teacher:avaliacoes')}?aluno={aluno_id}")


# ---------------------------------------------------------------------------
# Card: Encaminhar
# ---------------------------------------------------------------------------


RECENT_LIMIT = 5


class EncaminharView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "teacher/encaminhamentos.html"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        patient = self.selected_patient(user)

        context["queue"] = [
            {"patient": referido, "selected": patient == referido}
            for referido in self.queue(user)
        ]
        context["patient"] = patient
        context["areas"] = self.teacher().acting_areas.order_by("nome")
        context["options"] = self.options(user, patient)
        context["recent"] = self.recent(user)
        return context

    def post(self, request, *args, **kwargs):
        user = request.user
        patient = self.selected_patient(user)
        if patient is None:
            messages.error(request, "Escolha o paciente a encaminhar.")
            return redirect("teacher:encaminhamentos")

        students = Student.objects.filter(
            current_advisor_id=user.pk, pk__in=request.POST.getlist("alunos")
        )
        if not students:
            messages.error(request, "Escolha ao menos um aluno para encaminhar.")
            return redirect("teacher:encaminhar", pk=patient.pk)

        area_id = request.POST.get("area", "").strip()
        area = (
            self.teacher().acting_areas.filter(pk=area_id).first()
            if area_id.isdigit()
            else None
        )
        if area is None:
            messages.error(request, "Escolha a área de atuação do caso.")
            return redirect("teacher:encaminhar", pk=patient.pk)

        for student in students:
            if not CaseAssignment.can_be_created_by(user, student=student):
                raise PermissionDenied("Este aluno não está sob sua orientação.")

        try:
            self.refer(patient, students, area)
        except ValidationError as erro:
            messages.error(request, erro.messages[0])
            return redirect("teacher:encaminhar", pk=patient.pk)

        messages.success(
            request,
            f"{patient.get_full_name()} encaminhado para {students.count()} aluno(s).",
        )
        return redirect("teacher:encaminhamentos")

    def teacher(self):
        return get_object_or_404(Teacher, pk=self.request.user.pk)

    @staticmethod
    def queue(user):
        return (
            Patient.objects.visible_to(user)
            .filter(
                flow_status=Patient.FlowStatus.REFERRED,
                responsible_teachers=user.pk,
            )
            .distinct()
            .order_by("-created_at")
        )

    def selected_patient(self, user):
        if self.kwargs.get("pk"):
            return get_object_or_404(self.queue(user), pk=self.kwargs["pk"])

        return self.queue(user).first()

    @staticmethod
    def options(user, patient):
        atendendo = (
            set(
                patient.assignment_history.filter(end_date__isnull=True).values_list(
                    "student_id", flat=True
                )
            )
            if patient
            else set()
        )
        alunos = Student.objects.filter(current_advisor_id=user.pk).order_by(
            "first_name", "last_name"
        )
        return [
            {
                "value": aluno.pk,
                "label": aluno.get_full_name(),
                "checked": aluno.pk in atendendo,
            }
            for aluno in alunos
        ]

    @staticmethod
    @transaction.atomic
    def refer(patient, students, area):
        for student in students:
            CaseAssignment.objects.assign(student, patient, acting_area=area)

    @staticmethod
    def recent(user):
        casos = (
            CaseAssignment.objects.visible_to(user)
            .select_related("patient", "student")
            .order_by("-start_date")[:RECENT_LIMIT]
        )
        return [
            {
                "title": caso.patient.get_full_name(),
                "subtitle": caso.student.get_full_name(),
                "label": "Em atendimento" if caso.end_date is None else "Encerrado",
                "level": "success" if caso.end_date is None else "neutral",
            }
            for caso in casos
        ]
