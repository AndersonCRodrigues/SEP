from django import forms
from django.contrib.auth.forms import UserCreationForm
from core.models import CustomUser


class AdministrativoCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
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
            "matricula",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.role = CustomUser.Role.ADMINISTRATIVO

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.Role.ADMINISTRATIVO
        if commit:
            user.save()
        return user

    def clean_matricula(self):
        matricula = self.cleaned_data.get("matricula")
        if not matricula:
            raise forms.ValidationError("Matrícula é obrigatória.")
        return matricula
