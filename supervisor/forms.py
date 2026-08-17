from django import forms
from core.forms import PERSONAL_FIELDS
from teacher.models import Teacher
from teacher.forms import ProfessorCreationForm


class SupervisorCreationForm(ProfessorCreationForm):
    class Meta:
        model = Teacher
        fields = PERSONAL_FIELDS

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
        supervisor = super().save(commit=False)
        supervisor.role = Teacher.Role.SUPERVISOR
        if commit:
            supervisor.save()
        return supervisor