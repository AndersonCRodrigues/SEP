from django.views.generic import TemplateView

from .access import CoordinatorOnly


class CoordinatorFeedbacksView(CoordinatorOnly, TemplateView):
    template_name = "supervisor/feedbacks.html"
