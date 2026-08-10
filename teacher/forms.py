from django import forms
from django.contrib.auth.forms import UserCreationForm
from core.models import CustomUser
from teacher.models import Teacher
from areas.models import AreaActing
import re


class VincularAlunoForm(forms.Form):
    aluno = forms.ModelChoiceField(queryset=None, label="Aluno Disponível")
    periodo = forms.CharField(
        label="Período (AAAA.1 ou AAAA.2)",
        max_length=6,
        widget=forms.TextInput(attrs={"placeholder": "2026.1"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from students.models import Student  
        self.fields["aluno"].queryset = Student.objects.filter(current_advisor__isnull=True)

    def clean_periodo(self):
        periodo = self.cleaned_data["periodo"]
        if not re.match(r"^\d{4}\.[12]$", periodo):
            raise forms.ValidationError("Formato inválido. Use AAAA.1 ou AAAA.2 (ex: 2026.1).")
        return periodo


class ProfessorCreationForm(UserCreationForm):
    acting_area = forms.ModelChoiceField(
        queryset=AreaActing.objects.all(),
        label="Área de Atuação / Abordagem Teórica",
        empty_label="Selecione uma área...",
        required=False,
    )

    class Meta:
        model = Teacher
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
            "crp",
            "acting_area",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.role = CustomUser.Role.PROFESSOR

    def save(self, commit=True):
        professor = super().save(commit=False)
        professor.role = CustomUser.Role.PROFESSOR
        professor.acting_area = self.cleaned_data.get("acting_area")
        if commit:
            professor.save()
        return professor

    def clean_matricula(self):
        matricula = self.cleaned_data.get("matricula")
        if not matricula:
            raise forms.ValidationError("Matrícula é obrigatória.")
        return matricula

    def clean_crp(self):
        crp = self.cleaned_data.get("crp")
        if not crp:
            raise forms.ValidationError("CRP é obrigatório.")
        return crp


class PerfilProfessorForm(forms.ModelForm):
    class Meta:
        model = Teacher
        fields = ["acting_area"]
        labels = {"acting_area": "Área de Atuação / Abordagem Teórica"}