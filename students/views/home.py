from django.db import DatabaseError
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from core.month_calendar import displayed_month, month_calendar, month_range
from scheduling.models import Appointment
from triage.models import TriageFeedback

from ..models import CaseAssignment
from .access import StudentOnly
from .mocks import feedback_status
from .queue import waiting_patients

Status = Appointment.Status


class HomeEstudanteView(StudentOnly, TemplateView):
    template_name = "student/home.html"

    UNAVAILABLE = "Não foi possível carregar suas informações agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            context.update(self.overview(self.request.user, timezone.localtime()))
        except DatabaseError:
            context["home_error"] = self.UNAVAILABLE

        return context

    def overview(self, user, now):
        today = now.date()
        open_cases = (
            CaseAssignment.objects.visible_to(user)
            .filter(end_date__isnull=True)
            .select_related("patient", "acting_area")
        )
        triages = waiting_patients()

        return self.calendar(user, today) | {
            "indicators": [
                {"label": "Triagens pendentes", "value": triages.count()},
                {
                    "label": "Encaminhamentos hoje",
                    "value": open_cases.filter(start_date=today).count(),
                },
                {"label": "Pacientes ativos", "value": open_cases.count()},
                {"label": "Faltas", "value": self.absences(user)},
            ],
            "activities": [
                self.triage_activity(triages.first()),
                self.referral_activity(open_cases.order_by("-start_date").first()),
                self.feedback_activity(self.latest_feedback(user), now),
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
    def absences(user):
        return (
            Appointment.objects.visible_to(user)
            .filter(status=Status.STUDENT_NO_SHOW)
            .count()
        )

    @staticmethod
    def latest_feedback(user):
        return (
            TriageFeedback.objects.visible_to(user)
            .select_related("author")
            .order_by("-updated_at")
            .first()
        )

    @staticmethod
    def triage_activity(patient):
        activity = {
            "kind": "triage",
            "url": reverse("students:triagens"),
            "link_label": "Ver triagens a realizar",
        }
        if patient is None:
            return activity | {"title": "Nenhum paciente aguardando triagem."}

        desde = timezone.localtime(patient.created_at)
        return activity | {
            "title": f"Triagem - {patient.get_full_name()}",
            "detail": f"Aguardando desde {desde:%d/%m/%Y}",
            "label": "Pendente",
            "level": "warning",
        }

    @staticmethod
    def referral_activity(case):
        activity = {
            "kind": "referral",
            "url": reverse("students:encaminhamentos"),
            "link_label": "Ver encaminhamentos recebidos",
        }
        if case is None:
            return activity | {"title": "Nenhum encaminhamento recebido."}

        return activity | {
            "title": "Encaminhamento concluído",
            "detail": f"{case.patient.get_full_name()} em {case.acting_area.nome}",
            "label": "Ativo",
            "level": "success",
        }

    @staticmethod
    def feedback_activity(feedback, now):
        activity = {
            "kind": "feedback",
            "url": reverse("students:feedbacks"),
            "link_label": "Ver feedbacks recebidos",
        }
        if feedback is None:
            return activity | {"title": "Nenhum feedback recebido."}

        label, level = feedback_status(feedback.created_at, feedback.updated_at, now)
        return activity | {
            "title": f"Feedback {label.lower()}",
            "detail": f"Triagem revisada por {feedback.author.get_full_name()}",
            "label": label,
            "level": level,
        }
