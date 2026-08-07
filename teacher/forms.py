from django import forms
from django.contrib.auth.forms import UserCreationForm
from core.models import CustomUser
from teacher.models import Professor
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
        from students.models import Aluno  # import local: evita ciclo teacher <-> students
        self.fields["aluno"].queryset = Aluno.objects.filter(orientador_atual__isnull=True)

    def clean_periodo(self):
        periodo = self.cleaned_data["periodo"]
        if not re.match(r"^\d{4}\.[12]$", periodo):
            raise forms.ValidationError("Formato inválido. Use AAAA.1 ou AAAA.2 (ex: 2026.1).")
        return periodo


class ProfessorCreationForm(UserCreationForm):
    area_atuacao = forms.ModelChoiceField(
        queryset=AreaActing.objects.all(),
        label="Área de Atuação / Abordagem Teórica",
        empty_label="Selecione uma área...",
        required=False,
    )

    class Meta:
        model = Professor  # Alterado para Professor!
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
            "area_atuacao",
        )

    def save(self, commit=True):
        professor = super().save(commit=False)
        professor.role = CustomUser.Role.PROFESSOR
        professor.area_atuacao = self.cleaned_data.get("area_atuacao")
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
        model = Professor
        fields = ["area_atuacao"]
        labels = {"area_atuacao": "Área de Atuação / Abordagem Teórica"}