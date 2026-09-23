from django.utils import timezone
from django.views.generic import DetailView, ListView

from core.constants import TriageStatus
from triage.models import TriageRecord

from .access import CoordinatorOnly
from .mocks import submitted_at, triage_status

COLUMNS = ("Pacientes:", "Realizada por:", "Recebida:", "Status:", "")
QUEUE_STATUS = (TriageStatus.SUBMITTED, TriageStatus.CLOSED, TriageStatus.REFERRED)
SITUATIONS = (
    ("analisar", "Analisar"),
    ("atrasada", "Atrasada"),
    ("editada", "Editada"),
)


def received_label(moment, now):
    moment = timezone.localtime(moment)
    days = (now.date() - moment.date()).days

    if days == 0:
        return f"Recebida às {moment:%H:%M}"
    if days == 1:
        return "Recebida ontem"

    return f"Recebida em {moment:%d/%m/%Y}"


class CoordinatorTriagesView(CoordinatorOnly, ListView):
    template_name = "supervisor/triagens.html"
    context_object_name = "triagens"

    def get_queryset(self):
        return (
            TriageRecord.objects.visible_to(self.request.user)
            .filter(status__in=QUEUE_STATUS)
            .select_related("patient", "student_author")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.localtime()
        situacao = self.request.GET.get("situacao", "")

        linhas = []
        for record in context["triagens"]:
            label, level = triage_status(record, now)
            if situacao and label.lower() != situacao:
                continue
            linhas.append(
                {
                    "triage": record,
                    "patient": record.patient.get_full_name(),
                    "student": record.student_author.get_full_name(),
                    "received": received_label(submitted_at(record), now),
                    "label": label,
                    "level": level,
                }
            )

        context["columns"] = COLUMNS
        context["situations"] = SITUATIONS
        context["situation_filter"] = situacao
        context["rows"] = linhas
        return context


class CoordinatorTriageDetailView(CoordinatorOnly, DetailView):
    template_name = "supervisor/triagem_detalhe.html"
    context_object_name = "triagem"

    def get_queryset(self):
        return TriageRecord.objects.visible_to(self.request.user).select_related(
            "patient", "student_author", "closed_by"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        record = context["triagem"]
        now = timezone.localtime()
        label, level = triage_status(record, now)

        context["label"] = label
        context["level"] = level
        context["received"] = received_label(submitted_at(record), now)
        context["risk"] = record.get_risk_classification()
        context["can_refer"] = record.status != TriageStatus.REFERRED
        return context
