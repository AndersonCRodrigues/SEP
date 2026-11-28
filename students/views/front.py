"""Telas do front para a área do Aluno, em rota própria.

O desenho novo convive com as telas de `triages.py`, `referrals.py` e
`feedbacks.py`, que são as que têm consulta e recorte por visibilidade.
"""

from django.views.generic import TemplateView

from utils.masking import student_patient_label

from ..models import Student
from .access import StudentOnly


class TriagemAlunoView(StudentOnly, TemplateView):
    template_name = "student/student_triage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aluno = Student.objects.filter(pk=self.request.user.pk).first()
        casos = (
            aluno.open_cases.select_related("patient", "acting_area") if aluno else []
        )
        context["casos_abertos"] = [
            {
                "patient_id": caso.patient_id,
                "patient_label": student_patient_label(caso.patient),
                "acting_area": caso.acting_area,
                "start_date": caso.start_date,
                "responsible": getattr(caso, "responsible", ""),
            }
            for caso in casos
        ]
        return context


class EncaminhamentosAlunoView(StudentOnly, TemplateView):
    template_name = "student/student_referral.html"


class FeedbacksAlunoView(StudentOnly, TemplateView):
    template_name = "student/student_feedback.html"
