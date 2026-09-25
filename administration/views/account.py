from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from core.models import CustomUser
from core.utils import sincronizar_grupo

from ..forms import AdministrativoCreationForm
from .access import AdministrativeOnly


class PainelAdministracaoView(AdministrativeOnly, TemplateView):
    template_name = "administration/administration_panel.html"


class PerfilAdministrativoView(AdministrativeOnly, UpdateView):
    model = CustomUser
    fields = [
        "first_name",
        "last_name",
        "telefone",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cidade",
        "estado",
        "cep",
    ]
    template_name = "administration/perfil.html"
    success_url = reverse_lazy("administration:perfil")

    def get_object(self, queryset=None):
        return self.request.user


@login_required
def cadastrar_administrativo(request):
    if not request.user.has_perm("core.add_customuser"):
        raise PermissionDenied("Apenas o Superadmin pode cadastrar Administrativo.")

    if request.method == "POST":
        form = AdministrativoCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            sincronizar_grupo(user)
            messages.success(request, "Administrativo cadastrado com sucesso!")
            return redirect("superadmin:painel")
    else:
        form = AdministrativoCreationForm()

    return render(request, "administration/cadastro.html", {"form": form})
