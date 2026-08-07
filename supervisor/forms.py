from core.models import CustomUser
from teacher.forms import ProfessorCreationForm


class SupervisorCreationForm(ProfessorCreationForm):
    

    def save(self, commit=True):
        supervisor = super().save(commit=False)
        supervisor.role = CustomUser.Role.SUPERVISOR
        if commit:
            supervisor.save()
        return supervisor