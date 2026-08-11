from django import forms

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