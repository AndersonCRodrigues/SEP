import copy
from dataclasses import dataclass

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    IarvAdolescent,
    IarvAdult,
    IarvChild,
    TriageRecord,
)


class TriageRecordForm(forms.ModelForm):
    class Meta:
        model = TriageRecord
        exclude = (
            "patient",
            "student_author",
            "status",
            "closed_by",
            "closed_at",
            "submitted_at",
        )


class IarvAdultForm(forms.ModelForm):
    class Meta:
        model = IarvAdult
        exclude = ("triage_record",)


class IarvAdolescentForm(forms.ModelForm):
    class Meta:
        model = IarvAdolescent
        exclude = ("triage_record",)


class IarvChildForm(forms.ModelForm):
    class Meta:
        model = IarvChild
        exclude = ("triage_record",)


def get_iarv_form_class(patient):
    age = patient.current_age

    if age is None:
        raise ValidationError(
            "A data de nascimento do paciente é obrigatória para selecionar o questionário IARV."
        )
    if age < 13:
        return IarvChildForm
    if age <= 17:
        return IarvAdolescentForm
    return IarvAdultForm


def get_iarv_form_class_for_instance(iarv):
    if isinstance(iarv, IarvChildForm.Meta.model):
        return IarvChildForm
    if isinstance(iarv, IarvAdolescentForm.Meta.model):
        return IarvAdolescentForm
    return IarvAdultForm


SESSION_KEY = "triage_registration"

RISK_SECTION = "Instrumento de risco"
SECTIONS = (
    "Identificação",
    "Vínculo institucional",
    "Contexto clínico",
    "Rede de apoio",
    "Encerramento",
    RISK_SECTION,
)

SECTION_STARTS = {
    "arrival_method": "Identificação",
    "is_university_student": "Vínculo institucional",
    "chief_complaint": "Contexto clínico",
    "has_primary_care_connection": "Rede de apoio",
    "treatment_expectations": "Encerramento",
}

SECTION_BARS = 3

BOOLEAN_CHOICES = (("true", "Sim"), ("false", "Não"))


def _as_question(field):
    """O campo da ficha vira a pergunta da vez: sim/não em botão e texto em caixa."""
    if isinstance(field, forms.BooleanField):
        return forms.ChoiceField(
            label=field.label,
            required=field.required,
            choices=BOOLEAN_CHOICES,
            widget=forms.RadioSelect,
        )

    if isinstance(field, forms.ChoiceField) and not isinstance(
        field, forms.MultipleChoiceField
    ):
        field.choices = [
            (valor, rotulo)
            for valor, rotulo in field.choices
            if valor not in ("", None)
        ]
        field.widget = forms.RadioSelect(choices=field.choices)
        return field

    if isinstance(field.widget, (forms.TextInput, forms.Textarea)):
        field.widget = forms.Textarea(attrs={"rows": 6, "placeholder": "Resposta..."})

    return field


def _single_field_form_class(source_form_class, field_name):
    """Gera dinamicamente uma forms.Form contendo só um campo de source_form_class."""
    field = _as_question(copy.deepcopy(source_form_class.base_fields[field_name]))
    return type(
        f"{source_form_class.__name__}__{field_name}",
        (forms.Form,),
        {field_name: field},
    )


@dataclass(frozen=True)
class TriageStep:
    slug: str
    section: str
    title: str
    source: str  # "triagem" ou "iarv"
    field_name: str


class TriageRegistration:
    def __init__(self, session, patient):
        self.session = session
        self.patient = patient
        self.session_key = self._session_key(patient.pk)
        self.answers = session.get(self.session_key, {})

    @staticmethod
    def _session_key(patient_id):
        return f"{SESSION_KEY}:{patient_id}"

    @classmethod
    def start(cls, session, patient):
        session[cls._session_key(patient.pk)] = {}
        return cls(session, patient)

    @property
    def iarv_form_class(self):
        return get_iarv_form_class(self.patient)  # pode levantar ValidationError

    def steps(self):
        steps = []
        section = SECTIONS[0]
        for name, field in TriageRecordForm.base_fields.items():
            section = SECTION_STARTS.get(name, section)
            steps.append(
                TriageStep(f"triagem__{name}", section, field.label, "triagem", name)
            )

        iarv_form_class = self.iarv_form_class
        steps += [
            TriageStep(f"iarv__{name}", RISK_SECTION, field.label, "iarv", name)
            for name, field in iarv_form_class.base_fields.items()
        ]
        return steps

    def step(self, slug):
        return next((s for s in self.steps() if s.slug == slug), None)

    def neighbours(self, step):
        steps = self.steps()
        index = steps.index(step)
        previous = steps[index - 1] if index else None
        following = steps[index + 1] if index + 1 < len(steps) else None
        return previous, following

    def source_form_class(self, step):
        return TriageRecordForm if step.source == "triagem" else self.iarv_form_class

    def field_form_class(self, step):
        return _single_field_form_class(self.source_form_class(step), step.field_name)

    def answer(self, step):
        return self.answers.get(step.slug, {})

    def save(self, step, data):
        form_class = self.field_form_class(step)
        self.answers[step.slug] = {
            name: data.get(name, "") for name in form_class.base_fields
        }
        self.session[self.session_key] = self.answers

    def first_unanswered(self):
        return next(
            (
                s
                for s in self.steps()
                if not self.field_form_class(s)(data=self.answer(s)).is_valid()
            ),
            None,
        )

    def is_ahead(self, step):
        pending = self.first_unanswered()
        steps = self.steps()
        return pending is not None and steps.index(step) > steps.index(pending)

    def number(self, step):
        return self.steps().index(step) + 1

    def sections(self, current):
        steps = self.steps()
        position = SECTIONS.index(current.section)

        resumo = []
        for index, name in enumerate(SECTIONS):
            state = self.section_state(index, position)
            da_secao = [step for step in steps if step.section == name]
            resumo.append(
                {
                    "name": name,
                    "state": state,
                    "bars": self.section_bars(state, da_secao, current),
                }
            )
        return resumo

    @staticmethod
    def section_bars(state, section_steps, current):
        if state == "done":
            cheias = SECTION_BARS
        elif state == "pending" or not section_steps:
            cheias = 0
        else:
            lugar = section_steps.index(current) + 1
            cheias = -(-lugar * SECTION_BARS // len(section_steps))
        return [posicao < cheias for posicao in range(SECTION_BARS)]

    @staticmethod
    def section_state(index, position):
        if index < position:
            return "done"
        if index == position:
            return "current"
        return "pending"

    def _merged_data(self, source):
        merged = {}
        for step in self.steps():
            if step.source == source:
                merged.update(self.answer(step))
        return merged

    @transaction.atomic
    def complete(self, student_author):
        triage_form = TriageRecordForm(data=self._merged_data("triagem"))
        if not triage_form.is_valid():
            raise ValidationError(triage_form.errors)

        triage_record = triage_form.save(commit=False)
        triage_record.patient = self.patient
        triage_record.student_author = student_author
        triage_record.save()

        iarv_form = self.iarv_form_class(data=self._merged_data("iarv"))
        if not iarv_form.is_valid():
            triage_record.delete()
            raise ValidationError(iarv_form.errors)

        iarv = iarv_form.save(commit=False)
        iarv.triage_record = triage_record
        iarv.save()

        triage_record.submit(student_author)
        self.session.pop(self.session_key, None)
        return triage_record
