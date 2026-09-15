from django import forms
from django.utils import timezone
from core.models import CustomUser
from scheduling.models import AppointmentRequest
from .models import Patient


class PacienteCreationForm(forms.ModelForm):
    data_nascimento = forms.DateField(
        label="Data de Nascimento",
        widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"class": "date-picker", "placeholder": "Selecione a data"},
        ),
        input_formats=["%Y-%m-%d", "%d/%m/%Y"],
    )

    social_name = forms.CharField(
        label="Nome Social",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Nome social (opcional)"}),
    )

    gender_identity = forms.CharField(
        label="Identidade de Gênero",
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "Ex: Cissexual, Transgênero, Não-binário..."}
        ),
    )

    class Meta:
        model = Patient
        fields = (
            "email",
            "first_name",
            "last_name",
            "social_name",
            "gender_identity",
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
        self.created_by_user = None  # Evita AttributeError se não for passado pela view

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

        cleaned_data = self.cleaned_data.copy()
        cleaned_data["role"] = CustomUser.Role.PACIENTE

        return Patient.objects.create_with_credentials(
            raw_data=cleaned_data,
            created_by_user=self.created_by_user,
            commit=True,
        )


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
