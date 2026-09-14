from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, TemplateView, UpdateView
from core.constants import TriageStatus
from core.mixins import GroupRequiredMixin
from core.models import CustomUser
from django.contrib.auth.decorators import login_required
from scheduling.models import Appointment, AppointmentRequest
from triage.models import TriageRecord
from .forms import AppointmentRequestForm
from .models import Patient

Status = Appointment.Status
Presence = Appointment.PresenceStatus
RequestStatus = AppointmentRequest.Status
FlowStatus = Patient.FlowStatus

SESSION_STATUS = {
    Status.ATTENDED: ("Concluída", "success"),
    Status.PATIENT_NO_SHOW: ("Faltou", "danger"),
    Status.STUDENT_NO_SHOW: ("Não realizada", "warning"),
    Status.CANCELLED: ("Cancelada", "secondary"),
}

PRESENCE_LEVELS = {
    Presence.CONFIRMED: "success",
    Presence.AWAITING: "warning",
    Presence.SCHEDULED: "secondary",
}

REQUEST_LEVELS = {
    RequestStatus.PENDING: "warning",
    RequestStatus.ACCEPTED: "success",
    RequestStatus.DECLINED: "danger",
}

SESSION_TITLES = {
    Status.ATTENDED: "Sessão concluída",
    Status.PATIENT_NO_SHOW: "Falta registrada",
    Status.STUDENT_NO_SHOW: "Sessão não realizada",
    Status.CANCELLED: "Sessão cancelada",
}

NOT_STARTED = ("Não iniciada", "secondary", "Sua triagem ainda não começou.")

TRIAGE_STATUS = {
    FlowStatus.IN_TRIAGE: (
        "Em andamento",
        "warning",
        "Sua triagem está sendo feita pela equipe.",
    ),
    FlowStatus.AWAITING_REVIEW: (
        "Em análise",
        "warning",
        "Sua triagem está em análise pela supervisão.",
    ),
    FlowStatus.REFERRED: (
        "Concluída",
        "success",
        "Triagem encaminhada para acompanhamento.",
    ),
    FlowStatus.IN_TREATMENT: (
        "Concluída",
        "success",
        "Triagem concluída e acompanhamento em andamento.",
    ),
    FlowStatus.DISCHARGED: ("Concluída", "success", "Triagem concluída."),
}


def relative_day(day, today):
    difference = (day - today).days
    if difference == 0:
        return "Hoje"
    if difference == 1:
        return "Amanhã"
    if difference == -1:
        return "Ontem"
    return f"{day:%d/%m/%Y}"


def attendant_name(appointment):
    attendant = appointment.assigned_student or appointment.teacher
    return attendant.get_full_name() if attendant else ""


def session_badge(appointment, now):
    presence = appointment.presence_status(now)
    if presence:
        return presence.label, PRESENCE_LEVELS[presence]
    return SESSION_STATUS[appointment.status]


def upcoming_appointments(user, today):
    return (
        Appointment.objects.visible_to(user)
        .filter(status=Status.SCHEDULED, scheduled_at__date__gte=today)
        .select_related("assigned_student", "teacher")
        .order_by("scheduled_at")
    )


HISTORY_STATUS = SESSION_STATUS | {
    Status.SCHEDULED: ("Aguardando registro", "secondary"),
}

HISTORY_MESSAGES = {
    Status.ATTENDED: "Sessão realizada.",
    Status.PATIENT_NO_SHOW: "Sua falta foi registrada nesta sessão.",
    Status.STUDENT_NO_SHOW: "A sessão não aconteceu por ausência de quem atenderia.",
    Status.CANCELLED: "Esta sessão foi cancelada.",
    Status.SCHEDULED: "O registro desta sessão ainda não foi feito pela equipe.",
}


def history_appointments(user, today):
    return (
        Appointment.objects.visible_to(user)
        .filter(~Q(status=Status.SCHEDULED) | Q(scheduled_at__date__lt=today))
        .select_related("assigned_student", "teacher")
        .order_by("-scheduled_at")
    )


TRIAGE_OUTCOMES = {
    TriageStatus.REFERRED: {
        "label": "Encaminhada",
        "level": "success",
        "summary": "e já encaminhada para acompanhamento.",
        "closed_by_label": "Encaminhada por",
        "closed_at_label": "Encaminhada em",
    },
    TriageStatus.CLOSED: {
        "label": "Encerrada",
        "level": "secondary",
        "summary": "e encerrada sem encaminhamento para acompanhamento.",
        "closed_by_label": "Encerrada por",
        "closed_at_label": "Encerrada em",
    },
}

TRIAGE_IN_PROGRESS = (FlowStatus.IN_TRIAGE, FlowStatus.AWAITING_REVIEW)


def concluded_triages(user):
    return (
        TriageRecord.objects.visible_to(user)
        .select_related("closed_by")
        .only(
            "id",
            "status",
            "created_at",
            "closed_at",
            "closed_by",
            "closed_by__first_name",
            "closed_by__last_name",
        )
        .order_by("-created_at")
    )


class PatientOnly(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == CustomUser.Role.PACIENTE


class PatientHomeView(PatientOnly, TemplateView):
    template_name = "patient/home_patient.html"

    UPCOMING_SHOWN = 3
    UNAVAILABLE = "Não foi possível carregar suas informações agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.localtime()

        try:
            context.update(self.overview(user, now))
        except DatabaseError:
            context["home_error"] = self.UNAVAILABLE

        return context

    def overview(self, user, now):
        today = now.date()
        appointments = Appointment.objects.visible_to(user).select_related(
            "assigned_student", "teacher"
        )

        upcoming = list(upcoming_appointments(user, today)[: self.UPCOMING_SHOWN])
        last_session = (
            appointments.filter(scheduled_at__lt=now)
            .exclude(status=Status.SCHEDULED)
            .order_by("-scheduled_at")
            .first()
        )
        patient = Patient.objects.visible_to(user).first()
        triage = TRIAGE_STATUS.get(patient.flow_status if patient else "", NOT_STARTED)
        next_appointment = upcoming[0] if upcoming else None

        return {
            "sessions_done": appointments.filter(status=Status.ATTENDED).count(),
            "triage_status": triage[0],
            "next_session": (
                relative_day(self.local_day(next_appointment), today)
                if next_appointment
                else "Nenhuma"
            ),
            "absences": appointments.filter(status=Status.PATIENT_NO_SHOW).count(),
            "activities": [
                self.history_activity(last_session, today),
                self.appointment_activity(next_appointment, now),
                self.triage_activity(triage),
            ],
            "alert": self.today_alert(next_appointment, today),
            "upcoming": [self.as_event(appointment, today) for appointment in upcoming],
        }

    @staticmethod
    def local_day(appointment):
        return timezone.localtime(appointment.scheduled_at).date()

    @classmethod
    def when(cls, appointment, today):
        moment = timezone.localtime(appointment.scheduled_at)
        return f"{relative_day(moment.date(), today)} às {moment:%H:%M}"

    @classmethod
    def history_activity(cls, appointment, today):
        activity = {
            "kind": "history",
            "section": "Histórico",
            "url": reverse("patient:historico"),
            "link_label": "Ver histórico de sessões",
        }
        if appointment is None:
            return activity | {"title": "Nenhuma sessão realizada ainda."}

        label, level = SESSION_STATUS[appointment.status]
        return activity | {
            "title": SESSION_TITLES[appointment.status],
            "detail": cls.when(appointment, today),
            "label": label,
            "level": level,
        }

    @classmethod
    def appointment_activity(cls, appointment, now):
        activity = {
            "kind": "appointment",
            "section": "Agendamento",
            "url": reverse("patient:agendamentos"),
            "link_label": "Ver meus agendamentos",
        }
        if appointment is None:
            return activity | {"title": "Nenhuma sessão agendada."}

        label, level = session_badge(appointment, now)
        return activity | {
            "title": f"{appointment.get_kind_display()} agendada",
            "detail": cls.when(appointment, now.date()),
            "label": label,
            "level": level,
        }

    @staticmethod
    def triage_activity(triage):
        label, level, detail = triage
        return {
            "kind": "triage",
            "section": "Triagem",
            "title": f"Triagem {label.lower()}",
            "detail": detail,
            "label": label,
            "level": level,
            "url": reverse("patient:triagens"),
            "link_label": "Ver minhas triagens",
        }

    @classmethod
    def today_alert(cls, appointment, today):
        if appointment is None or cls.local_day(appointment) != today:
            return None
        return {
            "time": timezone.localtime(appointment.scheduled_at),
            "attendant": attendant_name(appointment),
        }

    @classmethod
    def as_event(cls, appointment, today):
        return {
            "when": timezone.localtime(appointment.scheduled_at),
            "day_label": relative_day(cls.local_day(appointment), today),
            "kind": appointment.get_kind_display(),
            "attendant": attendant_name(appointment),
        }


class PatientAppointmentsView(PatientOnly, TemplateView):
    template_name = "patient/agendamentos.html"

    COLUMN_LABELS = ("Data e hora:", "Atendimento por:", "Situação:")
    REQUESTS_SHOWN = 5
    UNAVAILABLE = "Não foi possível carregar seus agendamentos agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.localtime()
        context["column_labels"] = self.COLUMN_LABELS

        try:
            context["appointments"] = [
                self.as_row(appointment, now)
                for appointment in upcoming_appointments(user, now.date())
            ]
            context["schedule_requests"] = [
                self.as_request(item)
                for item in AppointmentRequest.objects.visible_to(user).order_by(
                    "-created_at"
                )[: self.REQUESTS_SHOWN]
            ]
        except DatabaseError:
            context.update(
                {
                    "appointments": [],
                    "schedule_requests": [],
                    "appointments_error": self.UNAVAILABLE,
                }
            )

        return context

    @staticmethod
    def as_row(appointment, now):
        moment = timezone.localtime(appointment.scheduled_at)
        label, level = session_badge(appointment, now)
        return {
            "when": moment,
            "when_label": f"{relative_day(moment.date(), now.date())} - {moment:%H:%M}",
            "attendant": attendant_name(appointment),
            "label": label,
            "level": level,
        }

    @staticmethod
    def as_request(item):
        return {
            "preferred_date": item.preferred_date,
            "period": item.get_preferred_period_display(),
            "label": item.get_status_display(),
            "level": REQUEST_LEVELS[item.status],
            "created_at": item.created_at,
            "response": item.response,
        }


class AppointmentRequestView(PatientOnly, FormView):
    template_name = "patient/solicitar_horario.html"
    form_class = AppointmentRequestForm
    success_url = reverse_lazy("patient:agendamentos")

    PENDING = "Você já tem uma solicitação de horário pendente."
    SENT = "Solicitação enviada. Aguarde a resposta do Administrativo."
    UNAVAILABLE = "Não foi possível registrar sua solicitação agora."
    NOT_FOUND = "Seu cadastro de paciente não foi encontrado."

    def test_func(self):
        return super().test_func() and AppointmentRequest.can_be_created_by(
            self.request.user
        )

    def pending_request(self):
        return (
            AppointmentRequest.objects.visible_to(self.request.user)
            .filter(status=RequestStatus.PENDING)
            .first()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["pending_request"] = self.pending_request()
        except DatabaseError:
            context["request_error"] = self.UNAVAILABLE
        return context

    def post(self, request, *args, **kwargs):
        try:
            pending = self.pending_request()
        except DatabaseError:
            messages.error(request, self.UNAVAILABLE)
            return redirect(self.success_url)

        if pending:
            messages.error(request, self.PENDING)
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        patient = Patient.objects.visible_to(self.request.user).first()
        if patient is None:
            form.add_error(None, self.NOT_FOUND)
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                form.save_for(patient)
        except IntegrityError:
            messages.error(self.request, self.PENDING)
            return redirect(self.success_url)
        except DatabaseError:
            form.add_error(None, self.UNAVAILABLE)
            return self.form_invalid(form)

        messages.success(self.request, self.SENT)
        return super().form_valid(form)


class PatientHistoryView(PatientOnly, TemplateView):
    template_name = "patient/historico.html"

    COLUMN_LABELS = ("Data e hora:", "Atendimento por:", "Situação:")
    PER_PAGE = 10
    UNAVAILABLE = "Não foi possível carregar seu histórico agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["column_labels"] = self.COLUMN_LABELS
        today = timezone.localdate()

        try:
            page = Paginator(
                history_appointments(self.request.user, today), self.PER_PAGE
            ).get_page(self.request.GET.get("pagina"))
            context.update(
                {
                    "page": page,
                    "sessions": [
                        self.as_row(appointment, today) for appointment in page
                    ],
                }
            )
        except DatabaseError:
            context.update({"sessions": [], "history_error": self.UNAVAILABLE})

        return context

    @staticmethod
    def as_row(appointment, today):
        moment = timezone.localtime(appointment.scheduled_at)
        label, level = HISTORY_STATUS[appointment.status]
        return {
            "pk": appointment.pk,
            "when": moment,
            "when_label": f"{relative_day(moment.date(), today)} - {moment:%H:%M}",
            "attendant": attendant_name(appointment),
            "label": label,
            "level": level,
        }


class PatientSessionDetailView(PatientOnly, TemplateView):
    template_name = "patient/historico_detalhe.html"

    UNAVAILABLE = "Não foi possível carregar esta sessão agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            appointment = (
                history_appointments(self.request.user, timezone.localdate())
                .filter(pk=self.kwargs["pk"])
                .first()
            )
        except DatabaseError:
            return context | {"session_error": self.UNAVAILABLE}

        if appointment is None:
            raise Http404("Sessão não encontrada.")

        context["session"] = self.as_detail(appointment)
        return context

    @staticmethod
    def as_detail(appointment):
        label, level = HISTORY_STATUS[appointment.status]
        return {
            "when": timezone.localtime(appointment.scheduled_at),
            "kind": appointment.get_kind_display(),
            "duration": appointment.duration_minutes,
            "attendant": attendant_name(appointment),
            "teacher": (
                appointment.teacher.get_full_name() if appointment.teacher else ""
            ),
            "label": label,
            "level": level,
            "message": HISTORY_MESSAGES[appointment.status],
        }


class PatientTriagesView(PatientOnly, TemplateView):
    template_name = "patient/triagens.html"

    UNAVAILABLE = "Não foi possível carregar suas triagens agora."
    IN_PROGRESS = "Há uma triagem em andamento. Quando ela for concluída, aparece aqui."
    EMPTY = "Você ainda não tem triagem concluída."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        try:
            triages = [self.as_item(triage) for triage in concluded_triages(user)]
            patient = Patient.objects.visible_to(user).only("flow_status").first()
        except DatabaseError:
            return context | {"triages": [], "triages_error": self.UNAVAILABLE}

        in_progress = bool(patient and patient.flow_status in TRIAGE_IN_PROGRESS)
        context.update(
            {
                "triages": triages,
                "in_progress": in_progress,
                "in_progress_message": self.IN_PROGRESS,
                "empty_message": self.IN_PROGRESS if in_progress else self.EMPTY,
            }
        )
        return context

    @staticmethod
    def as_item(triage):
        outcome = TRIAGE_OUTCOMES[triage.status]
        return {
            "pk": triage.pk,
            "created_at": timezone.localtime(triage.created_at),
            "label": outcome["label"],
            "level": outcome["level"],
        }


class PatientTriageDetailView(PatientOnly, TemplateView):
    template_name = "patient/triagem_detalhe.html"

    UNAVAILABLE = "Não foi possível carregar esta triagem agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        try:
            triage = concluded_triages(user).filter(pk=self.kwargs["pk"]).first()
            teachers = (
                self.responsible_teachers(user)
                if triage and triage.status == TriageStatus.REFERRED
                else []
            )
        except DatabaseError:
            return context | {"triage_error": self.UNAVAILABLE}

        if triage is None:
            raise Http404("Triagem não encontrada.")

        context["triage"] = self.as_detail(triage, teachers)
        return context

    @staticmethod
    def responsible_teachers(user):
        patient = Patient.objects.visible_to(user).first()
        if patient is None:
            return []
        return [
            teacher.get_full_name()
            for teacher in patient.responsible_teachers.only(
                "first_name", "last_name"
            ).order_by("first_name", "last_name")
        ]

    @staticmethod
    def as_detail(triage, teachers):
        return {
            **TRIAGE_OUTCOMES[triage.status],
            "created_at": timezone.localtime(triage.created_at),
            "closed_at": (
                timezone.localtime(triage.closed_at) if triage.closed_at else None
            ),
            "closed_by": triage.closed_by.get_full_name() if triage.closed_by else "",
            "teachers": teachers,
        }


class PatientContactView(PatientOnly, TemplateView):
    template_name = "patient/contato.html"


class EditarDadosPacienteView(GroupRequiredMixin, UpdateView):
    required_group = "Patient"
    model = CustomUser
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
    template_name = "patient/edit_data.html"
    success_url = reverse_lazy("patient:home")

    def get_object(self, queryset=None):
        # o paciente só pode editar o próprio cadastro
        return self.request.user


@login_required
def enviar_email(request):
    if request.method == "POST":
        pass
