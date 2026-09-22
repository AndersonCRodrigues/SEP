from django.views.generic import TemplateView

from .access import StudentOnly


class StudentReferralsView(StudentOnly, TemplateView):
    template_name = "student/encaminhamentos.html"
