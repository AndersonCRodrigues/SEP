from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from core.constants import TriageStatus
from triage.models import TriageFeedback, TriageRecord

from .access import CoordinatorOnly

COLUMNS = ("Aluno:", "Paciente:", "Situação:", "")
ANALYZED = (TriageStatus.CLOSED, TriageStatus.REFERRED)
SITUATIONS = (("pendentes", "A enviar"), ("enviados", "Enviados"))


class CoordinatorFeedbacksView(CoordinatorOnly, TemplateView):
    template_name = "supervisor/feedbacks.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        situacao = self.request.GET.get("situacao", "")

        linhas = []
        for record in self.analyzed(user):
            enviado = record.pareceres > 0
            if situacao == "enviados" and not enviado:
                continue
            if situacao == "pendentes" and enviado:
                continue
            linhas.append(
                {
                    "triage": record,
                    "student": record.student_author.get_full_name(),
                    "patient": record.patient.get_full_name(),
                    "label": "Enviado" if enviado else "Enviar",
                    "level": "success" if enviado else "danger",
                    "sent": enviado,
                }
            )

        context["columns"] = COLUMNS
        context["situations"] = SITUATIONS
        context["situation_filter"] = situacao
        context["rows"] = linhas
        context["chosen"] = self.chosen_triage(user)
        return context

    def post(self, request, *args, **kwargs):
        triagem = get_object_or_404(
            self.analyzed(request.user), pk=request.POST.get("triagem")
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
    def analyzed(user):
        return (
            TriageRecord.objects.visible_to(user)
            .filter(status__in=ANALYZED)
            .select_related("patient", "student_author")
            .annotate(pareceres=Count("feedbacks"))
            .order_by("-closed_at")
        )

    def chosen_triage(self, user):
        escolhida = self.request.GET.get("triagem", "")
        if not escolhida.isdigit():
            return None

        return self.analyzed(user).filter(pk=escolhida).first()
