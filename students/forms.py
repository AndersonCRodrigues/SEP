from django import forms
from django.contrib.auth.forms import UserCreationForm

from core.models import CustomUser

from .models import TERM_VALIDATOR, Student


class AlunoCreationForm(UserCreationForm):
    periodo = forms.CharField(
        label="Período (AAAA.1 ou AAAA.2)",
        max_length=6,
        required=False,
        validators=[TERM_VALIDATOR],
        widget=forms.TextInput(attrs={"placeholder": "2026.1"}),
    )

    field_order = [
        "email",
        "first_name",
        "last_name",
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
        "periodo",
        "current_advisor",
    ]

    class Meta:
        model = Student
        fields = (
            "email",
            "first_name",
            "last_name",
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
            "current_advisor",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.role = CustomUser.Role.ALUNO
        self.fields["current_advisor"].label = "Professor responsável"
        self.fields["current_advisor"].required = False

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("periodo") and not cleaned_data.get("current_advisor"):
            self.add_error(
                "periodo",
                "Escolha o professor responsável para registrar o período.",
            )
        return cleaned_data

    def save(self, commit=True):
        aluno = super().save(commit=False)
        aluno.role = CustomUser.Role.ALUNO
        # O periodo e do vinculo com o professor: quem grava e o signal de
        # Student, que le _advising_term ao abrir a orientacao.
        periodo = self.cleaned_data.get("periodo")
        if periodo:
            aluno._advising_term = periodo
        if commit:
            aluno.save()
        return aluno

    def clean_matricula(self):
        matricula = self.cleaned_data.get("matricula")
        if not matricula:
            raise forms.ValidationError("Matrícula é obrigatória.")
        return matricula
