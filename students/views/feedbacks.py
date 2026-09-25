from django.db import DatabaseError
from django.utils import timezone
from django.views.generic import TemplateView

from patient.models import ProgressNote
from triage.models import TriageFeedback

from .access import StudentOnly
from .dates import received_label
from .mocks import feedback_status

COLUMNS = ("Referente a:", "Realizada por:", "Recebida:", "Status:")


class StudentFeedbacksView(StudentOnly, TemplateView):
    template_name = "student/feedbacks.html"

    UNAVAILABLE = "Não foi possível carregar os feedbacks agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["columns"] = COLUMNS

        try:
            context["feedbacks"] = self.feedbacks(
                self.request.user, timezone.localtime()
            )
        except DatabaseError:
            context["feedbacks_error"] = self.UNAVAILABLE

        return context

    @classmethod
    def feedbacks(cls, user, now):
        received = cls.triage_feedbacks(user) + cls.record_feedbacks(user)
        received.sort(key=lambda item: item["moment"], reverse=True)

        for item in received:
            label, level = feedback_status(item["moment"], item["changed"], now)
            item["received"] = received_label(item["moment"], now)
            item["label"] = label
            item["level"] = level

        return received

    @staticmethod
    def triage_feedbacks(user):
        return [
            {
                "subject": f"Triagem - {feedback.triage.patient.get_full_name()}",
                "author": feedback.author.get_full_name(),
                "moment": feedback.created_at,
                "changed": feedback.updated_at,
            }
            for feedback in TriageFeedback.objects.visible_to(user).select_related(
                "author", "triage__patient"
            )
        ]

    @staticmethod
    def record_feedbacks(user):
        return [
            {
                "subject": f"Prontuário - {note.patient.get_full_name()}",
                "author": note.confirmed_by.get_full_name(),
                "moment": note.confirmed_at,
                "changed": note.updated_at,
            }
            for note in ProgressNote.objects.visible_to(user)
            .filter(confirmed_at__isnull=False)
            .select_related("confirmed_by", "patient")
        ]
