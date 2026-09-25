from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from core.models import CustomUser
from core.utils import sincronizar_grupo
from core.notifications import enviar_credenciais_por_telefone
from supervisor.utils import gerar_senha_temporaria, enviar_email_credenciais
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
            user = form.save(commit=False)

            senha_temporaria = gerar_senha_temporaria()
            user.set_password(senha_temporaria)
            user.must_change_password = True
            user.save()   

               

            sincronizar_grupo(user)

            email_ok = enviar_email_credenciais(user, senha_temporaria)
            telefone_ok = enviar_credenciais_por_telefone(user, senha_temporaria)

            if email_ok and telefone_ok:
                messages.success(request, "Administrativo cadastrado e credenciais enviadas com sucesso!")
            else:
                messages.warning(
                    request,
                    "Administrativo cadastrado, mas houve falha ao enviar as credenciais. "
                    "Verifique o log de auditoria e informe a senha manualmente se necessario.",
                )
            return redirect("superadmin:home")
    else:
        form = AdministrativoCreationForm()

    return render(request, "administration/cadastro.html", {"form": form})