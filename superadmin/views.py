from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView, UpdateView
from core.models import CustomUser
from core.mixins import GroupRequiredMixin


class PainelSuperadminView(GroupRequiredMixin, ListView):
    required_group = "Superadmin"
    model = CustomUser
    template_name = "superadmin/superadmin_panel.html"
    context_object_name = "todos_usuarios"

    def get_queryset(self):
        return CustomUser.objects.all().order_by("-id")


class HomeSuperadminView(GroupRequiredMixin, TemplateView):
    required_group = "Superadmin"
    template_name = "superadmin/home_superadmin.html"


class PerfilSuperadminView(GroupRequiredMixin, UpdateView):
    required_group = "Superadmin"
    model = CustomUser
    template_name = "superadmin/perfil.html"
    success_url = reverse_lazy("superadmin:perfil")

    def get_object(self, queryset=None):
        return self.request.user
