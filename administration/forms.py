import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from localflavor.br.br_states import STATE_CHOICES
from localflavor.br.forms import BRCPFField
from core.fields import format_cep, only_digits
from core.models import CustomUser
from core.validators import NO_NUMBER, validate_letters, validate_phone
from documents.models import AttendanceCertificate
from patient.models import Patient
from scheduling.models import Appointment
from students.models import Student

PATIENT = "patient"
STUDENT = "student"


class AdministrativoCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
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


class AppointmentDateField(forms.ModelChoiceField):
    def label_from_instance(self, appointment):
        return f"{timezone.localtime(appointment.scheduled_at):%d/%m/%Y às %H:%M}"


class MedicalCertificateForm(forms.Form):
    person = forms.ChoiceField(
        label="Nome do paciente ou aluno",
        choices=(),
        error_messages={
            "required": "Escolha o paciente ou o aluno.",
            "invalid_choice": "Escolha um paciente ou aluno válido.",
        },
    )

    appointment = AppointmentDateField(
        label="Data do atendimento",
        queryset=Appointment.objects.none(),
        empty_label="Escolha a pessoa para ver os atendimentos",
        error_messages={
            "required": "Escolha a data do atendimento.",
            "invalid_choice": (
                "Escolha uma data da lista de atendimentos dessa pessoa."
            ),
        },
    )

    notes = forms.CharField(
        label="Observações (opcional)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["person"].choices = self.person_choices(user)
        self.fields["appointment"].queryset = self.appointments_for(
            self.data.get("person"), user
        )
        if self.data.get("person"):
            self.fields["appointment"].empty_label = "Escolha a data do atendimento"

    @staticmethod
    def person_choices(user):
        if user is None:
            return [("", "---------")]

        return (
            [("", "---------")]
            + [
                (f"{PATIENT}:{person.pk}", str(person))
                for person in Patient.objects.visible_to(user)
            ]
            + [
                (f"{STUDENT}:{person.pk}", str(person))
                for person in Student.objects.all()
            ]
        )

    @staticmethod
    def appointments_for(person, user):
        kind, _, identifier = (person or "").partition(":")
        if not (user and identifier.isdigit()):
            return Appointment.objects.none()

        attended = (
            Appointment.objects.visible_to(user)
            .filter(status=Appointment.Status.ATTENDED)
            .order_by("-scheduled_at")
        )
        if kind == PATIENT:
            return attended.filter(patient_id=identifier)
        if kind == STUDENT:
            return attended.filter(assigned_student_id=identifier)
        return Appointment.objects.none()

    @staticmethod
    def resolve(person):
        kind, _, identifier = (person or "").partition(":")
        model = {PATIENT: Patient, STUDENT: Student}.get(kind)
        if model is None or not identifier.isdigit():
            return None

        found = model.objects.filter(pk=identifier).first()
        return (kind, found) if found else None

    def clean_person(self):
        person = self.cleaned_data["person"]
        if self.resolve(person) is None:
            raise forms.ValidationError("Escolha um paciente ou aluno válido.")
        return person

    def issue(self, issued_by):
        appointment = self.cleaned_data["appointment"]
        kind, person = self.resolve(self.cleaned_data["person"])
        when = timezone.localtime(appointment.scheduled_at)

        content = (
            "Compareceu ao atendimento no Serviço Escola de Psicologia em "
            f"{when:%d/%m/%Y} às {when:%H:%M}."
        )
        notes = self.cleaned_data.get("notes")
        if notes:
            content = f"{content}\n\n{notes}"

        return AttendanceCertificate.objects.create(
            patient=person if kind == PATIENT else None,
            student=person if kind == STUDENT else None,
            appointment=appointment,
            kind=AttendanceCertificate.Kind.MEDICAL_CERTIFICATE,
            status=AttendanceCertificate.Status.ISSUED,
            issued_at=timezone.localdate(),
            issued_by=issued_by,
            content=content,
        )


class RegistrationStepForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.error_messages["required"] = "Preencha este campo."
            field.error_messages.setdefault(
                "max_length", "Use no máximo %(limit_value)d caracteres."
            )
            field.error_messages.setdefault(
                "min_length", "Use no mínimo %(limit_value)d caracteres."
            )


class FullNameForm(RegistrationStepForm):
    first_name = forms.CharField(
        label="Nome",
        max_length=150,
        validators=[validate_letters],
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nome",
                "autocomplete": "given-name",
                "data-only": "letters",
            }
        ),
    )
    last_name = forms.CharField(
        label="Sobrenome",
        max_length=150,
        validators=[validate_letters],
        widget=forms.TextInput(
            attrs={
                "placeholder": "Sobrenome",
                "autocomplete": "family-name",
                "data-only": "letters",
            }
        ),
    )


class CpfForm(RegistrationStepForm):
    cpf = BRCPFField(
        label="CPF",
        max_length=None,
        min_length=None,
        widget=forms.TextInput(
            attrs={
                "placeholder": "ex: 000.000.000-00",
                "inputmode": "numeric",
                "maxlength": 14,
                "data-mask": "cpf",
            }
        ),
        error_messages={
            "invalid": "CPF inválido.",
            "max_digits": "O CPF tem 11 dígitos.",
        },
    )

    def clean_cpf(self):
        cpf = only_digits(self.cleaned_data["cpf"])
        if CustomUser.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError("Já existe um cadastro com este CPF.")
        return cpf


class BirthDateForm(RegistrationStepForm):
    data_nascimento = forms.DateField(
        label="Data de nascimento",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        error_messages={"invalid": "Informe uma data válida."},
    )

    def clean_data_nascimento(self):
        birth_date = self.cleaned_data["data_nascimento"]
        if birth_date > timezone.localdate():
            raise forms.ValidationError(
                "A data de nascimento não pode estar no futuro."
            )
        return birth_date


class PhoneForm(RegistrationStepForm):
    telefone = forms.CharField(
        label="Telefone de contato",
        validators=[validate_phone],
        widget=forms.TextInput(
            attrs={
                "placeholder": "ex: 21999999999",
                "inputmode": "numeric",
                "autocomplete": "tel",
                "maxlength": 11,
                "data-only": "digits",
            }
        ),
    )


class EmailForm(RegistrationStepForm):
    email = forms.EmailField(
        label="E-mail de contato",
        required=False,
        widget=forms.EmailInput(
            attrs={"placeholder": "ex: test@gmail.com", "autocomplete": "email"}
        ),
        error_messages={"invalid": "Informe um e-mail válido."},
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if email and CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe um cadastro com este e-mail.")
        return email


CEP_PATTERN = re.compile(r"^[0-9]{5}-?[0-9]{3}$")


class AddressForm(RegistrationStepForm):
    cep = forms.CharField(
        label="CEP",
        widget=forms.TextInput(
            attrs={
                "placeholder": "ex: 24900-000",
                "inputmode": "numeric",
                "maxlength": 9,
                "data-mask": "cep",
            }
        ),
    )
    logradouro = forms.CharField(label="Logradouro", max_length=200)
    numero = forms.CharField(
        label="Número",
        max_length=10,
        required=False,
        widget=forms.TextInput(
            attrs={"inputmode": "numeric", "maxlength": 10, "data-only": "digits"}
        ),
    )
    no_number = forms.BooleanField(label="S/N (sem número)", required=False)
    complemento = forms.CharField(label="Complemento", max_length=100, required=False)
    bairro = forms.CharField(label="Bairro", max_length=100)
    cidade = forms.CharField(
        label="Cidade",
        max_length=100,
        validators=[validate_letters],
        widget=forms.TextInput(
            attrs={"placeholder": "ex: Maricá", "data-only": "letters"}
        ),
    )
    estado = forms.ChoiceField(
        label="Estado",
        choices=[("", "---------"), *STATE_CHOICES],
        error_messages={"invalid_choice": "Escolha um estado válido."},
    )

    def clean_cep(self):
        cep = self.cleaned_data["cep"]
        if not CEP_PATTERN.match(cep):
            raise forms.ValidationError("Informe o CEP no formato 00000-000.")
        return format_cep(cep)

    def clean(self):
        cleaned_data = super().clean()
        number = cleaned_data.get("numero", "")
        if cleaned_data.pop("no_number", False):
            cleaned_data["numero"] = NO_NUMBER
        elif not number:
            self.add_error("numero", "Informe o número ou marque sem número.")
        elif not (number.isascii() and number.isdigit()):
            self.add_error("numero", "Use somente números.")
        return cleaned_data


class AccompaniedForm(RegistrationStepForm):
    is_accompanied = forms.TypedChoiceField(
        label="O paciente está acompanhado?",
        required=False,
        choices=(("sim", "Sim"), ("nao", "Não")),
        coerce=lambda answer: answer == "sim",
        empty_value=None,
        widget=forms.RadioSelect,
        error_messages={"invalid_choice": "Responda sim ou não."},
    )


class GuardianNameForm(RegistrationStepForm):
    guardian_first_name = forms.CharField(
        label="Nome do responsável",
        max_length=150,
        required=False,
        validators=[validate_letters],
        widget=forms.TextInput(
            attrs={"placeholder": "Nome do responsável", "data-only": "letters"}
        ),
    )
    guardian_last_name = forms.CharField(
        label="Sobrenome do responsável",
        max_length=150,
        required=False,
        validators=[validate_letters],
        widget=forms.TextInput(
            attrs={"placeholder": "Sobrenome do responsável", "data-only": "letters"}
        ),
    )


class GuardianRelationshipForm(RegistrationStepForm):
    guardian_relationship = forms.CharField(
        label="Grau de parentesco",
        max_length=100,
        required=False,
        validators=[validate_letters],
        widget=forms.TextInput(
            attrs={
                "placeholder": "Grau de parentesco do responsável",
                "data-only": "letters",
            }
        ),
    )
