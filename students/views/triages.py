from django.utils import timezone
from django.views.generic import DetailView, TemplateView

from triage.models import TriageRecord

from .access import StudentOnly
from .mocks import pending_triages

COLUMNS = ("Nome do paciente:", "Encaminhado por:", "Data do encaminhamento:", "Ação")


class StudentTriagesView(StudentOnly, TemplateView):
    template_name = "student/triagens.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["columns"] = COLUMNS
        context["triages"] = pending_triages(self.request.user)
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
            triage.closed_at or triage.created_at
        )
        return context
