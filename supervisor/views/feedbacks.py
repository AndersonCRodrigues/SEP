from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from core.constants import TriageStatus
from triage.models import TriageFeedback, TriageRecord

from .access import CoordinatorOnly

FINISHED = (
    TriageStatus.SUBMITTED,
    TriageStatus.FINALIZED_EDITION,
    TriageStatus.CLOSED,
    TriageStatus.REFERRED,
)


def situation(record):
    if record.pareceres:
        return "Enviado", "success"
    if record.status in FINISHED:
        return "Pendente", "danger"
    return "Em triagem", "secondary"


def student_feedbacks(user, student):
    pareceres = (
        TriageFeedback.objects.visible_to(user)
        .filter(triage__student_author=student)
        .select_related("author")
        .order_by("-updated_at")
    )
    return [
        {
            "author": parecer.author.get_full_name(),
            "when": parecer.updated_at,
            "content": parecer.content,
        }
        for parecer in pareceres
    ]


class CoordinatorFeedbacksView(CoordinatorOnly, TemplateView):
    template_name = "supervisor/feedbacks.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        search = self.request.GET.get("q", "").strip()
        escolhida = self.chosen_triage(user)

        linhas = []
        for record in self.triages(user, search):
            label, level = situation(record)
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

        context["search"] = search
        context["rows"] = linhas
        context["chosen"] = escolhida

        if escolhida:
            context["feedbacks"] = student_feedbacks(user, escolhida.student_author)

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
    def triages(user, search=""):
        registros = (
            TriageRecord.objects.visible_to(user)
            .select_related("patient", "student_author")
            .annotate(pareceres=Count("feedbacks"))
            .order_by("-created_at")
        )

        if search:
            registros = registros.filter(
                Q(student_author__first_name__icontains=search)
                | Q(student_author__last_name__icontains=search)
                | Q(patient__first_name__icontains=search)
                | Q(patient__last_name__icontains=search)
            )

        return registros

    @classmethod
    def writable(cls, user):
        return cls.triages(user).filter(status__in=FINISHED, pareceres=0)

    def chosen_triage(self, user):
        escolhida = self.request.GET.get("triagem", "")
        if not escolhida.isdigit():
            return None

        return self.writable(user).filter(pk=escolhida).first()
