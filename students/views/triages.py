from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, TemplateView

from triage.models import TriageRecord

from .access import StudentOnly
from .dates import updated_label
from .queue import waiting_patients

COLUMNS = ("Nome do paciente:", "Aguardando desde:", "Ação")


class StudentTriagesView(StudentOnly, TemplateView):
    template_name = "student/triagens.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.localtime()

        context["columns"] = COLUMNS
        context["triages"] = [
            {
                "patient": paciente,
                "name": paciente.get_full_name(),
                "waiting_since": paciente.created_at,
                "waiting_label": updated_label(paciente.created_at, now).replace(
                    "Atualizado", "Aguardando"
                ),
                "start_url": reverse("create_triage", args=[paciente.pk]),
            }
            for paciente in waiting_patients()
        ]
        return context


class TriageCompletedView(StudentOnly, DetailView):
    template_name = "student/triagem_concluida.html"
    context_object_name = "triage"

    def get_queryset(self):
        return TriageRecord.objects.visible_to(self.request.user).select_related(
            "patient", "student_author"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        triage = context["triage"]
        context["completed_at"] = timezone.localtime(
            triage.submitted_at or triage.closed_at or triage.created_at
        )
        return context
