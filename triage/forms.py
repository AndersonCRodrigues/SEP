import copy
from dataclasses import dataclass

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import (
    IarvAdult,
    IarvAdolescent,
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
SECTIONS = ("Triagem", "IARV")


def _single_field_form_class(source_form_class, field_name):
    """Gera dinamicamente uma forms.Form contendo só um campo de source_form_class."""
    field = copy.deepcopy(source_form_class.base_fields[field_name])
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
        steps = [
            TriageStep(f"triagem__{name}", "Triagem", field.label, "triagem", name)
            for name, field in TriageRecordForm.base_fields.items()
        ]
        iarv_form_class = self.iarv_form_class
        steps += [
            TriageStep(f"iarv__{name}", "IARV", field.label, "iarv", name)
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
        position = SECTIONS.index(current.section)
        return [
            {"name": name, "state": self.section_state(index, position)}
            for index, name in enumerate(SECTIONS)
        ]

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

        self.session.pop(self.session_key, None)
        return triage_record
