from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from core.fields import only_digits
from core.models import CustomUser
from scheduling.models import AppointmentRequest
from .models import Patient


class PacienteCreationForm(UserCreationForm):
    class Meta:
        # Patient, nao CustomUser: sem a linha filha da heranca multi-tabela o
        # paciente nao existe para Patient.objects nem para as FKs que o apontam.
        model = Patient
        fields = (
            "email",
            "first_name",
            "last_name",
            "cpf",
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
        for campo in ("password1", "password2"):
            self.fields[campo].required = False

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.Role.PACIENTE

        senha = self.cleaned_data.get("password1") or only_digits(user.cpf)
        user.set_password(senha)

        if commit:
            user.save()
        return user


class AppointmentRequestForm(forms.ModelForm):
    NOTES_LIMIT = 500

    notes = forms.CharField(
        label="Observações (opcional)",
        required=False,
        max_length=NOTES_LIMIT,
        widget=forms.Textarea(attrs={"rows": 4, "maxlength": NOTES_LIMIT}),
        error_messages={
            "max_length": "Use no máximo %(limit_value)d caracteres.",
        },
    )

    class Meta:
        model = AppointmentRequest
        fields = ("preferred_date", "preferred_period", "notes")
        widgets = {
            "preferred_date": forms.DateInput(
                attrs={"type": "date"}, format="%Y-%m-%d"
            ),
            "preferred_period": forms.RadioSelect,
        }
        error_messages = {
            "preferred_date": {
                "required": "Escolha a data de sua preferência.",
                "invalid": "Informe uma data válida.",
            },
            "preferred_period": {
                "required": "Escolha o período de sua preferência.",
                "invalid_choice": "Escolha um período da lista.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        date_field = self.fields["preferred_date"]
        date_field.input_formats = ["%Y-%m-%d"]
        date_field.widget.attrs["min"] = f"{timezone.localdate():%Y-%m-%d}"
        self.fields["preferred_period"].choices = AppointmentRequest.Period.choices

    def save_for(self, patient):
        self.instance.patient = patient
        return self.save()
