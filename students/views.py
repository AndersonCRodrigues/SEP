from django.views.generic import TemplateView
from core.mixins import GroupRequiredMixin


class PainelEstudanteView(GroupRequiredMixin, TemplateView):
    required_group = "Students"
    template_name = "student/student_panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estudante"] = self.request.user
        return context


class HomeEstudanteView(GroupRequiredMixin, TemplateView):
    required_group = "Students"
    template_name = "student/home_student.html"