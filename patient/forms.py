from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from core.fields import only_digits
from core.models import CustomUser
from .models import Patient


class PacienteCreationForm(UserCreationForm):

    data_nascimento = forms.DateField(
    label="Data de nascimento",
    widget=forms.DateInput(
        attrs={"class": "date-picker", "autocomplete": "off"},
        format="%Y-%m-%d",
    ),
    input_formats=["%Y-%m-%d"],
)

    class Meta:
        model = Patient
        fields = (
            "email",
            "nome_completo",
            "cpf",
            "social_name",
            "gender_identity",
            "data_nascimento",
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

        self.fields.pop("password1", None)
        self.fields.pop("password2", None)

    def clean_data_nascimento(self):
        data = self.cleaned_data.get("data_nascimento")
        if data and data > timezone.now().date():
            raise forms.ValidationError(
                "Data de nascimento não pode ser uma data futura."
            )
        return data

    def save(self, commit=True):
        if not commit:
            raise NotImplementedError(
                "PacienteCreationForm sempre precisa gerar credenciais; "
                "não há suporte a commit=False."
            )
        cleaned = {
            field: self.cleaned_data.get(field)
            for field in self.Meta.fields
        }
        return Patient.objects.create_with_credentials(**cleaned)


