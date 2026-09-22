from django.views.generic import TemplateView

from .access import StudentOnly


class HomeEstudanteView(StudentOnly, TemplateView):
    template_name = "student/home.html"
