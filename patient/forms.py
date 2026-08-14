from django.contrib.auth.forms import UserCreationForm
from core.models import CustomUser
from .models import Patient


class PacienteCreationForm(UserCreationForm):
    class Meta:
        # Patient, nao CustomUser: sem a linha filha da heranca multi-tabela o
        # paciente nao existe para Patient.objects nem para as FKs que o apontam.
        model = Patient
        fields = (
            "email",
            "nome_completo",
            "cpf",
            "telefone",
            "logradouro",
            "numero",
            "complemento",
            "bairro",
            "cidade",
            "estado",
            "cep",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.role = CustomUser.Role.PACIENTE

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.Role.PACIENTE
        if commit:
            user.save()
        return user
