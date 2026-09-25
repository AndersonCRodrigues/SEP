from django import forms

from core.forms import PERSONAL_FIELDS
from teacher.forms import ProfessorCreationForm
from teacher.models import Teacher


class SupervisorCreationForm(ProfessorCreationForm):
    class Meta:
        model = Teacher
        fields = tuple(
            f for f in PERSONAL_FIELDS
            if f not in ("logradouro", "numero", "complemento", "bairro", "cidade", "estado", "cep")
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (value, label)
            for value, label in Teacher.Role.choices
            if value == Teacher.Role.SUPERVISOR
        ]
        self.initial["role"] = Teacher.Role.SUPERVISOR

    def clean_role(self):
        role = self.cleaned_data["role"]
        if role != Teacher.Role.SUPERVISOR:
            raise forms.ValidationError(
                "Pelo Superadmin, só é possível cadastrar Supervisor."
            )
        return role

    def save(self, commit=True):
        supervisor = forms.ModelForm.save(self, commit=False)
        supervisor.role = Teacher.Role.SUPERVISOR

        if commit:
            supervisor.save()
            acting_areas = self.cleaned_data.get("acting_areas")
            if acting_areas:
                supervisor.acting_areas.set(acting_areas)

        return supervisor