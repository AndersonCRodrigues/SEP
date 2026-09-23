from django.views.generic import TemplateView

from .access import CoordinatorOnly


class CoordinatorReferralsView(CoordinatorOnly, TemplateView):
    template_name = "supervisor/encaminhamentos.html"
