from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser


class LoginEmailOuMatriculaForm(AuthenticationForm):

    username = forms.CharField(label="Email ou Matrícula")


class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = CustomUser
        fields = (
            "email", "nome_completo", "cpf", "telefone","data_nascimento", "logradouro",
            "numero", "complemento", "bairro", "cidade", "estado",
            "cep", "role", "crp", "matricula",
        )

    def __init__(self, *args, criado_por=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.criado_por = criado_por
        roles_bloqueados = [CustomUser.Role.SUPERVISOR, CustomUser.Role.SUPERADMIN]
        self.fields["role"].choices = [
            (cargo_valor, cargo_rotulo) for cargo_valor, cargo_rotulo in CustomUser.Role.choices
            if cargo_valor not in roles_bloqueados
        ]

    def clean_role(self):
        role = self.cleaned_data["role"]
        if role in (CustomUser.Role.SUPERVISOR, CustomUser.Role.SUPERADMIN):
            raise forms.ValidationError("Você não tem permissão para criar esse tipo de usuário.")
        return role

    def clean_matricula(self):
        matricula = self.cleaned_data.get("matricula")
        if not matricula:
            raise forms.ValidationError("Matrícula é obrigatória.")
        return matricula