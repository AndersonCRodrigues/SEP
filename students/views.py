from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView


class GroupRequiredMixin(UserPassesTestMixin):
    required_group = "Students"

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        return (
            self.request.user.groups.filter(name=self.required_group).exists() 
            or self.request.user.is_superuser
        )


class PainelEstudanteView(GroupRequiredMixin, TemplateView):
    template_name = "estudantes.html"  

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["estudante"] = self.request.user
        return context