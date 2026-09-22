from django.db import DatabaseError
from django.utils import timezone
from django.views.generic import TemplateView

from ..models import CaseAssignment
from .access import StudentOnly
from .mocks import referral_status

COLUMNS = ("Pacientes:", "Situação", "")


class StudentReferralsView(StudentOnly, TemplateView):
    template_name = "student/encaminhamentos.html"

    UNAVAILABLE = "Não foi possível carregar os encaminhamentos agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["columns"] = COLUMNS

        try:
            context["referrals"] = self.referrals(
                self.request.user, timezone.localtime().date()
            )
        except DatabaseError:
            context["referrals_error"] = self.UNAVAILABLE

        return context

    @staticmethod
    def referrals(user, today):
        return [
            {"patient": case.patient.get_full_name()} | referral_status(case, today)
            for case in CaseAssignment.objects.visible_to(user)
            .filter(end_date__isnull=True)
            .select_related("patient")
            .order_by("-start_date", "patient__first_name")
        ]
