from django.db import DatabaseError
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from core.month_calendar import displayed_month, month_calendar, month_range
from scheduling.models import Appointment

from ..models import Patient
from .access import PatientOnly
from .sessions import (
    SESSION_STATUS,
    Status,
    relative_day,
    session_badge,
    upcoming_appointments,
)

FlowStatus = Patient.FlowStatus

SESSION_TITLES = {
    Status.ATTENDED: "Sessão concluída",
    Status.PATIENT_NO_SHOW: "Falta registrada",
    Status.STUDENT_NO_SHOW: "Sessão não realizada",
    Status.CANCELLED: "Sessão cancelada",
}

NOT_STARTED = ("Não iniciada", "secondary", "Sua triagem ainda não começou.")

TRIAGE_STATUS = {
    FlowStatus.AWAITING_TRIAGE: NOT_STARTED,
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


class PatientHomeView(PatientOnly, TemplateView):
    template_name = "patient/home_patient.html"

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

        next_appointment = upcoming_appointments(user, today).first()
        last_session = (
            appointments.filter(scheduled_at__lt=now)
            .exclude(status=Status.SCHEDULED)
            .order_by("-scheduled_at")
            .first()
        )
        patient = Patient.objects.visible_to(user).first()
        triage = TRIAGE_STATUS.get(patient.flow_status if patient else "", NOT_STARTED)

        return self.calendar(user, today) | {
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
        }

    def calendar(self, user, today):
        year, month = displayed_month(self.request.GET, today)
        first, last = month_range(year, month)
        session_days = set(
            Appointment.objects.visible_to(user)
            .exclude(status=Status.CANCELLED)
            .filter(scheduled_at__date__range=(first, last))
            .dates("scheduled_at", "day")
        )
        return month_calendar(year, month, today, session_days)

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
