from django.contrib.auth.mixins import PermissionRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from areas.forms import AreaAtuacaoForm
from areas.models import AreaActing
from core.mixins import GroupRequiredMixin


class ListaAreasView(GroupRequiredMixin, ListView):
    required_group = "Supervisor"
    model = AreaActing
    template_name = "supervisor/area_list.html"
    context_object_name = "areas"


class CriarAreaView(PermissionRequiredMixin, CreateView):
    permission_required = "areas.add_areaacting"
    model = AreaActing
    form_class = AreaAtuacaoForm
    template_name = "supervisor/area_form.html"
    success_url = reverse_lazy("supervisor:areas")


class EditarAreaView(PermissionRequiredMixin, UpdateView):
    permission_required = "areas.change_areaacting"
    model = AreaActing
    form_class = AreaAtuacaoForm
    template_name = "supervisor/area_form.html"
    success_url = reverse_lazy("supervisor:areas")
