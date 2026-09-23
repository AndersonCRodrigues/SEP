from django.views.generic import TemplateView

from .access import CoordinatorOnly


class CoordinatorHomeView(CoordinatorOnly, TemplateView):
    template_name = "supervisor/home_supervisor.html"
