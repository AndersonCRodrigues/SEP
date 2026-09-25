from django.db import DatabaseError
from django.http import Http404
from django.utils import timezone
from django.views.generic import TemplateView

from core.constants import TriageStatus
from triage.models import TriageRecord

from ..models import Patient
from .access import PatientOnly

FlowStatus = Patient.FlowStatus

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
