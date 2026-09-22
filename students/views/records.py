from django.views.generic import TemplateView

from .access import StudentOnly


class StudentRecordsView(StudentOnly, TemplateView):
    template_name = "student/prontuarios.html"
