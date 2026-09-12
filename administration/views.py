from calendar import Calendar, monthrange
from datetime import date, datetime, time, timedelta

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from core.mixins import GroupRequiredMixin
from .forms import AdministrativoCreationForm
from core.utils import sincronizar_grupo
from core.models import CustomUser
from documents.models import AttendanceCertificate
from patient.forms import PacienteCreationForm
from scheduling.models import Appointment, Room, RoomBooking

MONTH_NAMES = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]

WEEKDAY_NAMES = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]

SCHEDULE_PERIODS = {
    "hoje": {"label": "Hoje", "heading": "Agenda de hoje"},
    "semana": {"label": "Esta semana", "heading": "Agenda da semana"},
    "mes": {"label": "Este mês", "heading": "Agenda do mês"},
    "todos": {"label": "Todos", "heading": "Agenda completa"},
}

STATUS_LEVELS = {
    Appointment.Status.SCHEDULED: "secondary",
    Appointment.Status.ATTENDED: "success",
    Appointment.Status.PATIENT_NO_SHOW: "warning",
    Appointment.Status.STUDENT_NO_SHOW: "warning",
    Appointment.Status.CANCELLED: "danger",
}


def day_label(day, today):
    """O desenho nomeia o dia em relacao a hoje, e so cai na data quando a
    semana nao basta para identificar o dia."""
    difference = (day - today).days
    if difference == 0:
        return "Hoje"
    if difference == -1:
        return "Ontem"
    if difference == 1:
        return "Amanhã"
    if abs(difference) < 7:
        return WEEKDAY_NAMES[day.weekday()]
    return f"{day:%d/%m/%Y}"


def period_range(period, today):
    if period == "hoje":
        return today, today
    if period == "semana":
        first = today - timedelta(days=(today.weekday() + 1) % 7)
        return first, first + timedelta(days=6)
    if period == "mes":
        last_day = monthrange(today.year, today.month)[1]
        return today.replace(day=1), today.replace(day=last_day)
    return None


@login_required
def cadastrar_paciente(request):
    is_administrativo = (
        request.user.is_superuser or request.user.role == CustomUser.Role.ADMINISTRATIVO
    )
    if not is_administrativo:
        raise PermissionDenied("Apenas o Administrativo pode cadastrar Paciente.")

    if request.method == "POST":
        form = PacienteCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            sincronizar_grupo(user)
            messages.success(request, "Paciente cadastrado com sucesso!")
            return redirect("administration:home")
    else:
        form = PacienteCreationForm()

    return render(request, "administration/cadastrar_paciente.html", {"form": form})


class AdministrativeOnly(LoginRequiredMixin, UserPassesTestMixin):
    """The whole administrative area answers only to the Administrativo."""

    def test_func(self):
        return (
            self.request.user.is_superuser
            or self.request.user.role == CustomUser.Role.ADMINISTRATIVO
        )


class PainelAdministracaoView(AdministrativeOnly, TemplateView):
    template_name = "administration/administration_panel.html"


class PerfilAdministrativoView(GroupRequiredMixin, UpdateView):
    required_group = "Administration"
    model = CustomUser
    fields = [
        "nome_completo",
        "telefone",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cidade",
        "estado",
        "cep",
    ]
    template_name = "administration/perfil.html"
    success_url = reverse_lazy("administration:perfil")

    def get_object(self, queryset=None):
        return self.request.user


@login_required
def cadastrar_administrativo(request):
    if not request.user.has_perm("core.add_customuser"):
        raise PermissionDenied("Apenas o Superadmin pode cadastrar Administrativo.")

    if request.method == "POST":
        form = AdministrativoCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            sincronizar_grupo(user)
            messages.success(request, "Administrativo cadastrado com sucesso!")
            return redirect("superadmin:painel")
    else:
        form = AdministrativoCreationForm()

    return render(request, "administration/cadastro.html", {"form": form})


class PatientsView(AdministrativeOnly, TemplateView):
    template_name = "administration/pacientes.html"


class ScheduleView(AdministrativeOnly, TemplateView):
    template_name = "administration/agenda.html"

    COLUMN_LABELS = ("Horário:", "Sala:", "Atendimento:", "Situação:")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()
        period = self.selected_period()

        context.update(
            {
                "heading": SCHEDULE_PERIODS[period]["heading"],
                "period_dates": self.period_dates(period, today),
                "column_labels": self.COLUMN_LABELS,
                "events": [
                    self.as_event(appointment, today)
                    for appointment in self.filtered(user, today, period)
                ],
            }
        )
        context.update(self.filter_options(user, period))
        return context

    def filtered(self, user, today, period):
        appointments = Appointment.objects.visible_to(user).select_related(
            "room", "patient", "assigned_student", "teacher"
        )

        span = period_range(period, today)
        if span:
            appointments = appointments.filter(scheduled_at__date__range=span)

        status = self.chosen("situacao", Appointment.Status.values)
        if status:
            appointments = appointments.filter(status=status)

        kind = self.chosen("tipo", Appointment.Kind.values)
        if kind:
            appointments = appointments.filter(kind=kind)

        room = self.chosen_room()
        if room:
            appointments = appointments.filter(room_id=room)

        return appointments

    def filter_options(self, user, period):
        return {
            "periods": SCHEDULE_PERIODS,
            "selected_period": period,
            "statuses": Appointment.Status.choices,
            "selected_status": self.chosen("situacao", Appointment.Status.values),
            "kinds": Appointment.Kind.choices,
            "selected_kind": self.chosen("tipo", Appointment.Kind.values),
            "rooms": Room.objects.visible_to(user).usable(),
            "selected_room": self.chosen_room(),
        }

    def chosen(self, parameter, allowed):
        """Query string e entrada do usuario: valor fora da lista nao filtra."""
        value = self.request.GET.get(parameter, "")
        return value if value in allowed else ""

    def chosen_room(self):
        room = self.request.GET.get("sala", "")
        return int(room) if room.isdigit() else None

    def selected_period(self):
        return self.chosen("periodo", SCHEDULE_PERIODS) or "hoje"

    @staticmethod
    def period_dates(period, today):
        span = period_range(period, today)
        if not span:
            return ""
        first, last = span
        if first == last:
            return f"{first:%d/%m/%Y}"
        if period == "mes":
            return f"{MONTH_NAMES[first.month - 1]} de {first.year}"
        return f"{first:%d/%m/%Y} a {last:%d/%m/%Y}"

    @staticmethod
    def as_event(appointment, today):
        when = timezone.localtime(appointment.scheduled_at)
        return {
            "appointment": appointment,
            "day_label": day_label(when.date(), today),
            "time": when,
            "status_level": STATUS_LEVELS.get(appointment.status, "secondary"),
            "attendant": appointment.assigned_student or appointment.teacher,
        }


class RoomsView(AdministrativeOnly, TemplateView):
    template_name = "administration/salas.html"


class DeclarationsView(AdministrativeOnly, TemplateView):
    template_name = "administration/declaracoes.html"


class CertificatesView(AdministrativeOnly, TemplateView):
    template_name = "administration/atestados.html"


class AdministrativeHomeView(AdministrativeOnly, TemplateView):
    template_name = "administration/home_administration.html"

    ACTIVITIES_SHOWN = 5

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        context.update(self.operational_summary(user, today))
        context["recent_activities"] = self.recent_activities(user)
        context.update(self.calendar_context(user, today))
        return context

    def operational_summary(self, user, today):
        occupied = (
            RoomBooking.objects.visible_to(user)
            .occupying(timezone.localtime())
            .filter(room__isnull=False)
            .values("room")
            .distinct()
            .count()
        )

        return {
            "occupied_rooms": occupied,
            "total_rooms": Room.objects.visible_to(user).usable().count(),
            "appointments_today": (
                Appointment.objects.visible_to(user)
                .filter(scheduled_at__date=today)
                .count()
            ),
            # TODO: documents has no pending status yet; the hook stays here.
            "pending_declarations": 0,
            "certificates_issued": (
                AttendanceCertificate.objects.visible_to(user)
                .filter(issued_at=today)
                .count()
            ),
        }

    def recent_activities(self, user):
        """Built from the business models, not from SecurityLog: the audit trail
        belongs to the Superadmin and the Administrativo cannot see it."""
        items = []

        for appointment in (
            Appointment.objects.visible_to(user)
            .select_related("room")
            .order_by("-created_at")[: self.ACTIVITIES_SHOWN]
        ):
            when = timezone.localtime(appointment.scheduled_at)
            items.append(
                {
                    "kind": "appointment",
                    "title": f"{appointment.get_kind_display()} agendada",
                    "detail": (
                        f"{appointment.room or 'Sem sala'} — {when:%d/%m às %H:%M}"
                    ),
                    "when": appointment.created_at,
                }
            )

        for document in (
            AttendanceCertificate.objects.visible_to(user)
            .select_related("patient")
            .order_by("-issued_at")[: self.ACTIVITIES_SHOWN]
        ):
            items.append(
                {
                    "kind": "document",
                    "title": f"{document.get_kind_display()} emitido",
                    "detail": str(document.patient),
                    "when": document.created_at,
                }
            )

        for booking in (
            RoomBooking.objects.visible_to(user)
            .select_related("room")
            .filter(end_date__isnull=False)
            .order_by("-end_date")[: self.ACTIVITIES_SHOWN]
        ):
            items.append(
                {
                    "kind": "room",
                    "title": "Sala liberada",
                    "detail": f"{booking.room or 'Sala removida'} — "
                    f"{booking.get_weekday_display()} {booking.start_time:%H:%M}",
                    "when": self.as_instant(booking.end_date),
                }
            )

        # Sorting by date alone ties everything that happened on the same day,
        # and the tie falls back to insertion order: one source takes the list.
        items.sort(key=lambda item: item["when"], reverse=True)
        return items[: self.ACTIVITIES_SHOWN]

    @staticmethod
    def as_instant(day):
        """RoomBooking.end_date is a date; the rest are datetimes."""
        return timezone.make_aware(datetime.combine(day, time.min))

    def calendar_context(self, user, today):
        year, month = self.displayed_month(today)
        first = date(year, month, 1)
        last = date(year, month, monthrange(year, month)[1])

        with_event = set(
            Appointment.objects.visible_to(user)
            .filter(scheduled_at__date__range=(first, last))
            .dates("scheduled_at", "day")
        )

        weeks = [
            [
                {
                    "date": day,
                    "in_month": day.month == month,
                    "today": day == today,
                    "has_event": day in with_event,
                }
                for day in week
            ]
            for week in Calendar(firstweekday=6).monthdatescalendar(year, month)
        ]

        return {
            "calendar_year": year,
            "calendar_month": month,
            "calendar_weeks": weeks,
            "calendar_months": list(enumerate(MONTH_NAMES, start=1)),
            "calendar_years": range(today.year - 2, today.year + 3),
            "previous_month": first - timedelta(days=1),
            "next_month": last + timedelta(days=1),
        }

    def displayed_month(self, today):
        """Query string is user input: it cannot bring the page down."""
        try:
            year = int(self.request.GET.get("ano", today.year))
            month = int(self.request.GET.get("mes", today.month))
            date(year, month, 1)
        except (TypeError, ValueError):
            return today.year, today.month
        return year, month
