from django.urls import reverse_lazy
from django.views.generic import UpdateView
from core.mixins import GroupRequiredMixin
from core.models import CustomUser
from django.contrib.auth.decorators import login_required


class EditarDadosPacienteView(GroupRequiredMixin, UpdateView):
    required_group = "Patient"
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
    template_name = "patient/edit_data.html"
    success_url = reverse_lazy("patient:home")

    def get_object(self, queryset=None):
        # o paciente só pode editar o próprio cadastro
        return self.request.user


@login_required
def enviar_email(request):
    if request.method == "POST":
        pass
