from django.views.generic import TemplateView

from .access import StudentOnly


class StudentTriagesView(StudentOnly, TemplateView):
    template_name = "student/triagens.html"


class TriageCompletedView(StudentOnly, TemplateView):
    template_name = "student/triagem_concluida.html"
