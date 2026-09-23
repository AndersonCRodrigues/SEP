from django.db import DatabaseError
from django.utils import timezone
from django.views.generic import TemplateView
from documents.models import AttendanceCertificate, InternshipDeclaration
from .access import AdministrativeOnly


class DeclarationsView(AdministrativeOnly, TemplateView):
    template_name = "administration/declaracoes.html"

    COLUMN_LABELS = ("Nome:", "Tipo:", "Referente a:", "Situação:")
    UNAVAILABLE = "Não foi possível consultar as declarações agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["column_labels"] = self.COLUMN_LABELS

        try:
            context["declarations"] = self.listed(self.request.user)
        except DatabaseError:
            context.update({"declarations": [], "declarations_error": self.UNAVAILABLE})

        return context

    def listed(self, user):
        rows = [
            self.as_row(
                document,
                "Paciente" if document.patient_id else "Aluno",
                document.person,
                f"Comparecimento — {self.reference(document):%d/%m/%Y}",
            )
            for document in AttendanceCertificate.objects.visible_to(user)
            .filter(kind=AttendanceCertificate.Kind.DECLARATION)
            .select_related("patient", "student")
        ]

        rows += [
            self.as_row(
                document,
                "Aluno",
                document.student,
                f"Estágio — {document.start_date:%d/%m/%Y} a "
                f"{document.end_date:%d/%m/%Y}",
            )
            for document in InternshipDeclaration.objects.visible_to(
                user
            ).select_related("student")
        ]

        rows.sort(key=lambda row: row["when"], reverse=True)
        return rows

    @staticmethod
    def reference(document):
        return document.issued_at or timezone.localdate(document.created_at)

    @classmethod
    def as_row(cls, document, person_kind, person, subject):
        return {
            "name": str(person),
            "person_kind": person_kind,
            "subject": subject,
            "label": document.get_status_display(),
            "level": (
                "success" if document.status == document.Status.ISSUED else "danger"
            ),
            "when": cls.reference(document),
        }
