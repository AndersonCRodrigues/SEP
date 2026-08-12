from django import forms
from django.contrib.auth.forms import UserCreationForm
from core.models import CustomUser
from .models import Aluno


class AlunoCreationForm(UserCreationForm):
    class Meta:
        model = Aluno
        fields = (
            "email", "nome_completo", "cpf", "telefone", "data_nascimento", "logradouro",
            "numero", "complemento", "bairro", "cidade", "estado",
            "cep", "matricula",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.role = CustomUser.Role.ALUNO

    def save(self, commit=True):
        aluno = super().save(commit=False)
        aluno.role = CustomUser.Role.ALUNO
        if commit:
            aluno.save()
        return aluno

    def clean_matricula(self):
        matricula = self.cleaned_data.get("matricula")
        if not matricula:
            raise forms.ValidationError("Matrícula é obrigatória.")
        return matricula