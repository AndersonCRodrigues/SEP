from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from core.models import CustomUser
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


class AppointmentDateField(forms.ModelChoiceField):
    def label_from_instance(self, appointment):
        return f"{timezone.localtime(appointment.scheduled_at):%d/%m/%Y às %H:%M}"


class MedicalCertificateForm(forms.Form):
    """A data do atendimento nao e digitada: ela sai da lista de atendimentos
    daquela pessoa. Assim nao ha como emitir atestado para data inexistente, e
    a escolha fora da lista e recusada pelo proprio campo."""

    # LANGUAGE_CODE e en-us: sem declarar as mensagens, o Django avisaria o
    # usuario em ingles.
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
                # Student nao tem escopo declarado como o Patient; esta tela e
                # so do Administrativo, que enxerga todos de qualquer forma.
                (f"{STUDENT}:{person.pk}", str(person))
                for person in Student.objects.all()
            ]
        )

    @staticmethod
    def appointments_for(person, user):
        """So atendimento que ja aconteceu gera atestado de comparecimento."""
        kind, _, identifier = (person or "").partition(":")
        if not (user and identifier.isdigit()):
            return Appointment.objects.none()

        attended = Appointment.objects.visible_to(user).filter(
            status=Appointment.Status.ATTENDED
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
