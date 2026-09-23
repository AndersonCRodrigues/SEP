from django.db import DatabaseError
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from core.constants import TriageStatus
from core.month_calendar import displayed_month, month_calendar, month_range
from core.models import CustomUser
from teacher.models import Teacher
from triage.models import TriageRecord

from .access import CoordinatorOnly
from .mocks import submitted_at

ANALYZED = (TriageStatus.CLOSED, TriageStatus.REFERRED)


class CoordinatorHomeView(CoordinatorOnly, TemplateView):
    template_name = "supervisor/home_supervisor.html"

    UNAVAILABLE = "Não foi possível carregar o resumo agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            context.update(self.overview(self.request.user, timezone.localtime()))
        except DatabaseError:
            context["home_error"] = self.UNAVAILABLE

        return context

    def overview(self, user, now):
        today = now.date()
        triages = TriageRecord.objects.visible_to(user).select_related(
            "patient", "student_author", "closed_by"
        )
        pending = triages.filter(status=TriageStatus.SUBMITTED)
        awaiting_feedback = (
            triages.filter(status__in=ANALYZED)
            .annotate(pareceres=Count("feedbacks"))
            .filter(pareceres=0)
        )

        return self.calendar(user, today) | {
            "indicators": [
                {"label": "Triagens pendentes", "value": pending.count()},
                {
                    "label": "Encaminhamentos hoje",
                    "value": triages.filter(
                        status=TriageStatus.REFERRED, closed_at__date=today
                    ).count(),
                },
                {"label": "Professores ativos", "value": self.active_teachers()},
                {"label": "Feedbacks a enviar", "value": awaiting_feedback.count()},
            ],
            "activities": [
                self.triage_activity(pending.order_by("-created_at").first()),
                self.referral_activity(
                    triages.filter(status=TriageStatus.REFERRED)
                    .order_by("-closed_at")
                    .first()
                ),
                self.feedback_activity(
                    awaiting_feedback.order_by("-closed_at").first()
                ),
            ],
        }

    def calendar(self, user, today):
        year, month = displayed_month(self.request.GET, today)
        first, last = month_range(year, month)
        triages = TriageRecord.objects.visible_to(user)
        days = set(
            triages.filter(created_at__date__range=(first, last)).dates(
                "created_at", "day"
            )
        ) | set(
            triages.filter(closed_at__date__range=(first, last)).dates(
                "closed_at", "day"
            )
        )
        return month_calendar(year, month, today, days)

    @staticmethod
    def active_teachers():
        return (
            Teacher.objects.filter(role=CustomUser.Role.PROFESSOR)
            .filter(Q(current_advisees__isnull=False))
            .distinct()
            .count()
        )

    @staticmethod
    def triage_activity(record):
        activity = {
            "kind": "triage",
            "url": reverse("supervisor:triagens"),
            "link_label": "Ver triagens para analisar",
        }
        if record is None:
            return activity | {"title": "Nenhuma triagem aguardando análise."}

        recebida = timezone.localtime(submitted_at(record))
        return activity | {
            "title": f"Triagem - {record.patient.get_full_name()}",
            "detail": f"Recebida às {recebida:%H:%M}",
            "label": "Pendente",
            "level": "warning",
        }

    @staticmethod
    def referral_activity(record):
        activity = {
            "kind": "referral",
            "url": reverse("supervisor:encaminhamentos"),
            "link_label": "Ver encaminhamentos",
        }
        if record is None:
            return activity | {"title": "Nenhum encaminhamento concluído."}

        return activity | {
            "title": "Encaminhamento concluído",
            "detail": f"{record.patient.get_full_name()} encaminhado ao professor",
            "label": "Concluído",
            "level": "success",
        }

    @staticmethod
    def feedback_activity(record):
        activity = {
            "kind": "feedback",
            "url": reverse("supervisor:feedbacks"),
            "link_label": "Ver feedbacks",
        }
        if record is None:
            return activity | {"title": "Nenhum parecer pendente."}

        return activity | {
            "title": "Feedback pendente",
            "detail": f"Triagem de {record.patient.get_full_name()} analisada",
            "label": "Pendente",
            "level": "warning",
        }
