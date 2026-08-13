from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from patient.models import Patient
from students.models import Student
from .forms import (
    IarvAdultForm,
    IarvAdolescentForm,
    IarvChildForm,
    TriageRecordForm,
)

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


@login_required
def create_triage(request, patient_id):
    patient = get_object_or_404(
        Patient,
        pk=patient_id,
    )

    try:
        student_author = Student.objects.get(pk=request.user.pk)
    except Student.DoesNotExist:
        raise ValidationError(
            "Apenas alunos podem criar uma ficha de triagem."
        )

    iarv_form_class = get_iarv_form_class(patient)

    if request.method == "POST":
        triage_form = TriageRecordForm(request.POST)
        iarv_form = iarv_form_class(request.POST)

        if triage_form.is_valid() and iarv_form.is_valid():
            with transaction.atomic():
                triage_record = triage_form.save(commit=False)

                triage_record.patient = patient
                triage_record.student_author = student_author
                triage_record.save()

                iarv = iarv_form.save(commit=False)
                iarv.triage_record = triage_record
                iarv.save()

            return redirect("home_redirect", pk=triage_record.pk)

    else:
        triage_form = TriageRecordForm()
        iarv_form = iarv_form_class()

    context = {
        "patient": patient,
        "triage_form": triage_form,
        "iarv_form": iarv_form,
        "patient_age": patient.current_age,
    }

    return render(
        request,
        "triage/create_triage.html",
        context,
    )