from django.views.generic import TemplateView

from .access import CoordinatorOnly


class CoordinatorTriagesView(CoordinatorOnly, TemplateView):
    template_name = "supervisor/triagens.html"
