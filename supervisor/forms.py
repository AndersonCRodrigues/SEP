from core.models import CustomUser
from teacher.forms import ProfessorCreationForm


class SupervisorCreationForm(ProfessorCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.role = CustomUser.Role.SUPERVISOR

    def save(self, commit=True):
        supervisor = super().save(commit=False)
        supervisor.role = CustomUser.Role.SUPERVISOR
        if commit:
            supervisor.save()
        return supervisor
