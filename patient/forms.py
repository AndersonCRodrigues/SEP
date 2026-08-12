from django.contrib.auth.forms import UserCreationForm
from core.models import CustomUser


class PacienteCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = (
            "email", "nome_completo", "cpf", "telefone", "data_nascimento", "logradouro",
            "numero", "complemento", "bairro", "cidade", "estado",
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