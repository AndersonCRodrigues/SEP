from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from core.constants import TriageStatus
from triage.models import TriageFeedback, TriageRecord

from .access import CoordinatorOnly

COLUMNS = ("Aluno:", "Paciente:", "Situação:", "")
FINISHED = (
    TriageStatus.SUBMITTED,
    TriageStatus.FINALIZED_EDITION,
    TriageStatus.CLOSED,
    TriageStatus.REFERRED,
)
SITUATIONS = (
    ("em_triagem", "Em triagem"),
    ("pendente", "Pendente"),
    ("enviado", "Enviado"),
)


def situation(record):
    if record.pareceres:
        return "Enviado", "success"
    if record.status in FINISHED:
        return "Pendente", "danger"
    return "Em triagem", "secondary"


class CoordinatorFeedbacksView(CoordinatorOnly, TemplateView):
    template_name = "supervisor/feedbacks.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        filtro = self.request.GET.get("situacao", "")

        linhas = []
        for record in self.triages(user):
            label, level = situation(record)
            if filtro and filtro != label.lower().replace(" ", "_"):
                continue
            linhas.append(
                {
                    "triage": record,
                    "student": record.student_author.get_full_name(),
                    "patient": record.patient.get_full_name(),
                    "label": label,
                    "level": level,
                    "can_write": label == "Pendente",
                }
            )

        context["columns"] = COLUMNS
        context["situations"] = SITUATIONS
        context["situation_filter"] = filtro
        context["rows"] = linhas
        context["chosen"] = self.chosen_triage(user)
        return context

    def post(self, request, *args, **kwargs):
        triagem = get_object_or_404(
            self.writable(request.user), pk=request.POST.get("triagem")
        )
        parecer = request.POST.get("parecer", "").strip()

        if not parecer:
            messages.error(request, "Escreva o feedback antes de enviar.")
            return redirect(f"{request.path}?triagem={triagem.pk}")

        TriageFeedback.objects.create(
            triage=triagem, author=request.user, content=parecer
        )
        messages.success(
            request,
            f"Feedback enviado para {triagem.student_author.get_full_name()}.",
        )
        return redirect(request.path)

    @staticmethod
    def triages(user):
        return (
            TriageRecord.objects.visible_to(user)
            .select_related("patient", "student_author")
            .annotate(pareceres=Count("feedbacks"))
            .order_by("-created_at")
        )

    @classmethod
    def writable(cls, user):
        return cls.triages(user).filter(status__in=FINISHED, pareceres=0)

    def chosen_triage(self, user):
        escolhida = self.request.GET.get("triagem", "")
        if not escolhida.isdigit():
            return None

        return self.writable(user).filter(pk=escolhida).first()
