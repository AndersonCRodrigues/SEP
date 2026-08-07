from core.models import CustomUser
from core.forms import UserCreationForm

class PacienteCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = (
            "email", "nome_completo", "cpf", "telefone", "logradouro",
            "numero", "complemento", "bairro", "cidade", "estado",
            "cep",
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.Role.PACIENTE
        if commit:
            user.save()
        return user