from django.utils import timezone
from django.views.generic import TemplateView
from core.month_calendar import MONTH_NAMES
from scheduling.models import Appointment, Room
from .access import AdministrativeOnly
from .dates import day_label, period_range

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
