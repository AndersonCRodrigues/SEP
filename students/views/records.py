from django.db import DatabaseError
from django.utils import timezone
from django.views.generic import TemplateView

from patient.models import ProgressNote

from ..models import CaseAssignment
from .access import StudentOnly
from .dates import updated_label
from .mocks import record_status

COLUMNS = ("Pacientes:", "Última evolução:", "Situação")


class StudentRecordsView(StudentOnly, TemplateView):
    template_name = "student/prontuarios.html"

    UNAVAILABLE = "Não foi possível carregar os prontuários agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["columns"] = COLUMNS

        try:
            context["records"] = self.records(self.request.user, timezone.localtime())
        except DatabaseError:
            context["records_error"] = self.UNAVAILABLE

        return context

    @classmethod
    def records(cls, user, now):
        latest = cls.latest_notes(user)
        rows = []

        for case in (
            CaseAssignment.objects.visible_to(user)
            .filter(end_date__isnull=True)
            .select_related("patient")
            .order_by("patient__first_name", "patient__last_name")
        ):
            note = latest.get(case.patient_id)
            label, level = record_status(note) if note else ("Pendente", "danger")
            rows.append(
                {
                    "patient": case.patient.get_full_name(),
                    "updated": updated_label(note.updated_at if note else None, now),
                    "label": label,
                    "level": level,
                }
            )

        return rows

    @staticmethod
    def latest_notes(user):
        notes = {}
        for note in ProgressNote.objects.visible_to(user).order_by("updated_at"):
            notes[note.patient_id] = note
        return notes
