from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from areas.models import AreaActing
from patient.models import Patient
from students.models import Student
from teacher.models import Teacher
from .models import CustomUser


PERSONAL_FIELDS = (
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
    "role",
    "crp",
    "matricula",
)


class LoginEmailOuMatriculaForm(AuthenticationForm):
    username = forms.CharField(label="Email ou Matrícula")


class CustomUserCreationForm(UserCreationForm):
    MODEL_BY_ROLE = {
        CustomUser.Role.PROFESSOR: Teacher,
        CustomUser.Role.ALUNO: Student,
        CustomUser.Role.PACIENTE: Patient,
    }

    ROLES_REQUIRING_REGISTRATION = (
        CustomUser.Role.ALUNO,
        CustomUser.Role.PROFESSOR,
    )

    acting_areas = forms.ModelMultipleChoiceField(
        queryset=AreaActing.objects.all(),
        required=False,
        label="Áreas de atuação",
        help_text="Obrigatório para Professor Responsável.",
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = CustomUser
        fields = PERSONAL_FIELDS + ("acting_areas",)

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")

        if role in self.ROLES_REQUIRING_REGISTRATION and not cleaned_data.get(
            "matricula"
        ):
            self.add_error(
                "matricula", "Matrícula é obrigatória para Aluno e Professor."
            )

        if role == CustomUser.Role.PROFESSOR and not cleaned_data.get("acting_areas"):
            self.add_error(
                "acting_areas", "Professor precisa de pelo menos uma área de atuação."
            )

        return cleaned_data

    def _post_clean(self):
        model = self.MODEL_BY_ROLE.get(self.cleaned_data.get("role"))
        if model is not None:
            self.instance = model()

        super()._post_clean()

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit and isinstance(user, Teacher):
            user.acting_areas.set(self.cleaned_data["acting_areas"])
        return user


class SupervisorCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = PERSONAL_FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (value, label)
            for value, label in CustomUser.Role.choices
            if value == CustomUser.Role.SUPERVISOR
        ]
        self.initial["role"] = CustomUser.Role.SUPERVISOR

    def clean_role(self):
        role = self.cleaned_data["role"]
        if role != CustomUser.Role.SUPERVISOR:
            raise forms.ValidationError(
                "Pelo admin, só é possível cadastrar Supervisor."
            )
        return role
