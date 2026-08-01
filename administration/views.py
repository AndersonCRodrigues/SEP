from django.views.generic import ListView, TemplateView
from core.models import CustomUser
from core.mixins import GroupRequiredMixin


class PainelAdministracaoView(GroupRequiredMixin, ListView):
    required_group = "Administration"
    model = CustomUser
    template_name = "administration/administration_panel.html"
    context_object_name = "atendimentos_ou_usuarios"

    def get_queryset(self):
        return CustomUser.objects.filter(
            role__in=[CustomUser.Role.ALUNO, CustomUser.Role.PROFESSOR]
        )


class HomeAdministracaoView(GroupRequiredMixin, TemplateView):
    required_group = "Administration"
    template_name = "administration/home_administration.html"