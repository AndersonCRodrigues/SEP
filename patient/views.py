from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView
from core.mixins import GroupRequiredMixin
from core.models import CustomUser
from django.contrib.auth.decorators import login_required


class HomePacienteView(GroupRequiredMixin, TemplateView):
    required_group = "Patient"
    template_name = "patient/home_patient.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["paciente"] = self.request.user
        context["agendamentos"] = [
            {"data": "05/08/2026", "descricao": "Sessão com Prof. Ana (Psicanálise)"},
            {"data": "12/08/2026", "descricao": "Sessão com Prof. Ana (Psicanálise)"},
        ]
        return context


class EditarDadosPacienteView(GroupRequiredMixin, UpdateView):
    required_group = "Patient"
    model = CustomUser
    fields = [
        "nome_completo",
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
