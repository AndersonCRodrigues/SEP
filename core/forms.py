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
    username = forms.CharField(label="Email, Matrícula ou CPF")


class CustomUserCreationForm(UserCreationForm):
    MODEL_BY_ROLE = {
        CustomUser.Role.PROFESSOR: Teacher,
        CustomUser.Role.SUPERVISOR: Teacher,
        CustomUser.Role.ALUNO: Student,
        CustomUser.Role.PACIENTE: Patient,
    }

    ROLES_REQUIRING_REGISTRATION = (
        CustomUser.Role.ALUNO,
        CustomUser.Role.PROFESSOR,
    )

    # O Supervisor tem area propria e supervisiona todas: o alcance vem das
    # permissoes, nao da ausencia de area.
    ROLES_REQUIRING_AREA = (
        CustomUser.Role.PROFESSOR,
        CustomUser.Role.SUPERVISOR,
    )

    acting_area = forms.ModelChoiceField(
        queryset=AreaActing.objects.all(),
        required=False,
        label="Área de atuação",
        help_text="Obrigatório para Professor e Supervisor.",
    )

    class Meta:
        model = CustomUser
        fields = PERSONAL_FIELDS

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")

        if role in self.ROLES_REQUIRING_REGISTRATION and not cleaned_data.get(
            "matricula"
        ):
            self.add_error(
                "matricula", "Matrícula é obrigatória para Aluno e Professor."
            )

        if role in self.ROLES_REQUIRING_AREA and not cleaned_data.get("acting_area"):
            self.add_error(
                "acting_area", "Professor e Supervisor precisam de área de atuação."
            )

        return cleaned_data

    def _post_clean(self):
        model = self.MODEL_BY_ROLE.get(self.cleaned_data.get("role"))
        if model is not None:
            self.instance = model()
            if model is Teacher:
                self.instance.acting_area = self.cleaned_data.get("acting_area")
        super()._post_clean()
