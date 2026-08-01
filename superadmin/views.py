from django.views.generic import ListView, TemplateView
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