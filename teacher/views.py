from django.shortcuts import render, redirect, get_object_or_404
from students.models import Advising, advisees_visible_to
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone
from django.views.generic import ListView, DetailView, TemplateView, UpdateView
from django.urls import reverse, reverse_lazy
from .forms import ProfessorCreationForm, PerfilProfessorForm
from .models import Teacher
from core.utils import sincronizar_grupo
from django.core.exceptions import ValidationError
from core.models import CustomUser
from .forms import VincularAlunoForm
from students.models import StudentActivity
from .forms import StudentActivityForm, PerformanceReviewForm


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
        import calendar
        from datetime import date, datetime

        from scheduling.models import Appointment

        try:
            mes = int(self.request.GET.get("mes", hoje.month))
            ano = int(self.request.GET.get("ano", hoje.year))
        except ValueError:
            mes, ano = hoje.month, hoje.year

        if not 1 <= mes <= 12 or not 1 <= ano <= 9999:
            mes, ano = hoje.month, hoje.year

        data_referencia = date(ano, mes, 1)
        mes_anterior, ano_anterior = (
            (12, ano - 1) if mes == 1 else (mes - 1, ano)
        )
        mes_seguinte, ano_seguinte = (
            (1, ano + 1) if mes == 12 else (mes + 1, ano)
        )

        # `scheduled_at` é guardado em UTC (USE_TZ=True), mas o "mês" que o
        # calendário mostra é o mês local (o mesmo usado por
        # timezone.localdate()/timezone.localtime()). Filtrar diretamente
        # por scheduled_at__year/__month compara o componente em UTC do
        # campo, não o local: um agendamento perto da virada do mês (ex.:
        # 31/01 22h no fuso local, já 01/02 de madrugada em UTC, ou o
        # inverso) pode aparecer no mês errado ou sumir do mês certo.
        # Por isso convertemos o mês local pedido num intervalo
        # timezone-aware [início, fim) e filtramos scheduled_at por esse
        # intervalo, em vez de pelos componentes de data/mês do campo.
        inicio_mes = timezone.make_aware(datetime(ano, mes, 1))
        inicio_mes_seguinte = timezone.make_aware(
            datetime(ano_seguinte, mes_seguinte, 1)
        )

        agendamentos_mes = Appointment.objects.visible_to(
            self.request.user
        ).filter(
            scheduled_at__gte=inicio_mes,
            scheduled_at__lt=inicio_mes_seguinte,
            status=Appointment.Status.SCHEDULED,
        )
        dias_com_agendamento = {
            timezone.localtime(dt).day
            for dt in agendamentos_mes.values_list("scheduled_at", flat=True)
        }

        cal = calendar.Calendar(firstweekday=6)  # semana começa no domingo

        return {
            "data_referencia": data_referencia,
            "semanas": cal.monthdayscalendar(ano, mes),
            "dias_com_agendamento": dias_com_agendamento,
            "dia_hoje": hoje.day if (hoje.year == ano and hoje.month == mes) else None,
            "mes_anterior": mes_anterior,
            "ano_anterior": ano_anterior,
            "mes_seguinte": mes_seguinte,
            "ano_seguinte": ano_seguinte,
        }

    def get_context_data(self, **kwargs):
        from patient.models import Patient, ProgressNote
        from students.models import Attendance, Student

        context = super().get_context_data(**kwargs)
        alunos = advisees_visible_to(self.request.user)

        hoje = timezone.localdate()
        context["calendario"] = self._montar_calendario(hoje)

        context["alunos_orientados_total"] = alunos.count()
        context["pacientes_ativos_total"] = (
            Patient.objects.visible_to(self.request.user)
            .filter(flow_status=Patient.FlowStatus.IN_TREATMENT)
            .count()
        )
        context["presentes_hoje"] = Attendance.objects.filter(
            student__in=alunos, date=hoje
        ).count()
        context["total_para_presenca"] = alunos.count()

        evolucoes_pendentes = ProgressNote.objects.visible_to(
            self.request.user
        ).filter(confirmed_at__isnull=True)
        context["avaliacoes_pendentes_total"] = evolucoes_pendentes.count()

        atividades = []
        for nota in evolucoes_pendentes.select_related("patient", "student").order_by(
            "-created_at"
        )[:5]:
            atividades.append(
                {
                    "tipo": "Prontuário",
                    "titulo": f"Evolução de {nota.patient.nome_completo}",
                    "detalhe": f"Aluno responsável: {nota.student.nome_completo}",
                    "quando": nota.created_at,
                    "url_name": "teacher:prontuario_detalhe",
                    "url_pk": nota.pk,
                }
            )

        for paciente in (
            Patient.objects.visible_to(self.request.user)
            .filter(flow_status=Patient.FlowStatus.REFERRED)
            .order_by("-created_at")[:5]
        ):
            atividades.append(
                {
                    "tipo": "Triagem",
                    "titulo": f"Encaminhamento — {paciente.nome_completo}",
                    "detalhe": "Aguardando definição de aluno responsável",
                    "quando": paciente.created_at,
                    "url_name": "teacher:triagem_definir",
                    "url_pk": paciente.pk,
                }
            )

        atividades.sort(key=lambda item: item["quando"], reverse=True)
        context["atividades_recentes"] = atividades[:5]
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


# COMENTADO a pedido do front (validação de 12/09): a decisão do Card 1 é
# que cada papel tenha uma única tela inicial (ver "Mapa de Rotas e
# Permissões", seção Card 1). teacher:home já absorveu resumo/atividades/
# calendário; falta só decidir onde os dois formulários abaixo (Vincular
# Aluno, Lançar Horas) vão morar antes de remover isto de vez. Comentado, não
# apagado, pra não perder a implementação. A rota em urls.py e o link na
# sidebar também estão comentados -- ver esses dois arquivos.
#
# class PainelProfessorView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
#     template_name = "teacher/teacher_panel.html"
#
#     def test_func(self):
#         return self.request.user.role in (
#             CustomUser.Role.PROFESSOR,
#             CustomUser.Role.SUPERVISOR,
#         )
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         from students.models import Student
#
#         professor = get_object_or_404(Teacher, pk=self.request.user.pk)
#         context["alunos_vinculados"] = professor.current_advisees.all()
#
#         context["alunos_disponiveis"] = Student.objects.filter(
#             current_advisor__isnull=True
#         )
#         context["form_vincular"] = VincularAlunoForm()
#         context["form_horas"] = StudentActivityForm(user=professor)
#         return context


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

    return redirect("teacher:alunos")


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

    return redirect("teacher:alunos")


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
        from patient.models import ProgressNote

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
        from patient.models import ProgressNote

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
# Card: Presença e feedback
# ---------------------------------------------------------------------------


class PresencaFeedbackView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "teacher/presenca_feedback.html"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get_context_data(self, **kwargs):
        from students.models import Attendance, PerformanceReview, Student

        context = super().get_context_data(**kwargs)
        alunos = advisees_visible_to(self.request.user).order_by("first_name", "last_name")

        # Busca por nome (a pedido do front, 19/09): igual à de "Meus
        # Alunos" -- filtra a lista antes de montar tabela/<select>, além
        # do filtro por aluno específico já existente logo abaixo.
        termo_busca = self.request.GET.get("q", "").strip()
        if termo_busca:
            alunos = alunos.filter(
                Q(first_name__icontains=termo_busca)
                | Q(last_name__icontains=termo_busca)
            )

        hoje = timezone.localdate()
        presencas_hoje = {
            registro.student_id: registro
            for registro in Attendance.objects.filter(student__in=alunos, date=hoje)
        }

        # Filtro por aluno (a pedido do front, validação de 12/09): quando
        # um aluno é escolhido no <select>, a tabela passa a mostrar só a
        # linha dele, em vez de todos os orientandos.
        aluno_id = self.request.GET.get("aluno", "").strip()
        # isdigit() evita ValueError do Django ao comparar string nao
        # numerica com pk inteiro (ex.: ?aluno=abc manipulado na URL).
        aluno_selecionado = (
            alunos.filter(pk=aluno_id).first()
            if aluno_id.isdigit()
            else None
        )
        alunos_para_tabela = [aluno_selecionado] if aluno_selecionado else alunos

        context["linhas"] = [
            {"aluno": aluno, "presenca": presencas_hoje.get(aluno.pk)}
            for aluno in alunos_para_tabela
        ]
        context["hoje"] = hoje
        context["alunos_para_filtro"] = alunos
        context["aluno_filtro_id"] = aluno_id
        context["termo_busca"] = termo_busca

        if aluno_selecionado:
            context["aluno_selecionado"] = aluno_selecionado
            context["form_feedback"] = PerformanceReviewForm()
            context["feedbacks_aluno"] = (
                PerformanceReview.objects.filter(student=aluno_selecionado)
                .select_related("teacher")
                .order_by("-updated_at")
            )

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

    return redirect(f"{reverse('teacher:presenca')}?aluno={aluno_id}")


# ---------------------------------------------------------------------------
# Card: Definição de realização de triagem
# ---------------------------------------------------------------------------


class TriagensPendentesView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = "teacher/triagens_lista.html"
    context_object_name = "pacientes"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get_queryset(self):
        from patient.models import Patient

        return (
            Patient.objects.visible_to(self.request.user)
            .filter(flow_status=Patient.FlowStatus.REFERRED)
            .order_by("first_name", "last_name")
        )


class DefinirTriagemView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    template_name = "teacher/triagem_definir.html"
    context_object_name = "paciente"
    pk_url_kwarg = "patient_id"

    def test_func(self):
        return self.request.user.role in (
            CustomUser.Role.PROFESSOR,
            CustomUser.Role.SUPERVISOR,
        )

    def get_queryset(self):
        from patient.models import Patient

        return Patient.objects.visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        from students.models import Student

        context = super().get_context_data(**kwargs)
        alunos = advisees_visible_to(self.request.user).order_by("first_name", "last_name")

        # MOCK: ainda não foi definido como produto/backend que essa tela do
        # Figma mapeia para CaseAssignment (limite de alunos por paciente).
        # Por ora, todo aluno vem habilitado e nenhum pré-marcado. Quando essa
        # integração virar task, trocar por CaseAssignment.objects.open() +
        # CaseAssignment.MAX_STUDENTS_PER_PATIENT.
        context["linhas"] = [
            {"aluno": aluno, "ja_designado": False, "habilitado": True}
            for aluno in alunos
        ]
        context["vagas_disponiveis"] = 2  # mock
        return context

    def post(self, request, *args, **kwargs):
        # MOCK: não persiste nada ainda — a integração real (CaseAssignment)
        # entra quando a task de "definição de triagem" for confirmada.
        paciente = self.get_object()
        alunos_selecionados = request.POST.getlist("alunos")

        if alunos_selecionados:
            messages.success(
                request,
                f"{len(alunos_selecionados)} aluno(s) selecionado(s) para "
                f"{paciente.nome_completo} (simulado).",
            )
        else:
            messages.warning(request, "Nenhum aluno foi selecionado.")

        return redirect("teacher:triagens")