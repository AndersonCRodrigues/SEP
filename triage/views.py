from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseForbidden

from patient.models import Patient
from students.models import Student
from teacher.models import Teacher
from areas.models import AreaActing
from core.models import CustomUser
from core.constants import TriageStatus
from triage.models import TriageRecord, TriageFeedback, Referral
from .forms import (
    IarvAdultForm,
    IarvAdolescentForm,
    IarvChildForm,
    TriageRecordForm,
)

Role = CustomUser.Role


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
def minhas_triagens(request):
    """
    Lista as triagens do próprio Aluno, pra ele conseguir voltar depois e
    ver o parecer do Supervisor — sem isso, a única forma de achar de novo
    a triagem era guardar a URL na mão.
    """
    if request.user.role != Role.ALUNO:
        return HttpResponseForbidden("Apenas Alunos podem acessar as próprias triagens.")

    triagens = TriageRecord.objects.filter(
        student_author_id=request.user.pk
    ).order_by("-created_at")

    return render(request, "triage/minhas_triagens.html", {"triagens": triagens})


@login_required
def fila_triagem(request):
    """
    Lista pacientes que ainda não foram reivindicados por nenhuma triagem
    (flow_status == "").  De propósito NÃO passa por
    Patient.objects.visible_to(request.user): nesse momento não existe
    posse nenhuma ainda pra filtrar, então usar o queryset role-scoped
    aqui sempre devolveria a fila vazia.
    """
    if request.user.role != Role.ALUNO:
        return HttpResponseForbidden("Apenas Alunos podem acessar a fila de triagem.")

    pacientes_aguardando = Patient.objects.filter(flow_status="")

    return render(
        request,
        "triage/fila_triagem.html",
        {"pacientes_aguardando": pacientes_aguardando},
    )


@login_required
def create_triage(request, patient_id):
    patient = get_object_or_404(
        Patient,
        pk=patient_id,
    )

    try:
        student_author = Student.objects.get(pk=request.user.pk)
    except Student.DoesNotExist:
        raise ValidationError("Apenas alunos podem criar uma ficha de triagem.")

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

           
            return redirect("triage_detail", pk=triage_record.pk)

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


@login_required
def submit_triage(request, pk):
    """Aluno envia a própria triagem OPEN pro Supervisor (OPEN -> SUBMITTED)."""
    triage = get_object_or_404(TriageRecord, pk=pk)

    try:
        triage.submit(request.user)
        messages.success(request, "Triagem enviada pro Supervisor.")
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("triage_detail", pk=pk)


@login_required
def triage_detail(request, pk):
    triage = get_object_or_404(TriageRecord, pk=pk)

    if request.user.role == Role.ALUNO and triage.status != TriageStatus.OPEN:
        context = {
            "paciente": triage.patient.nome_completo,
            "feedback_triage": triage.feedbacks.all(),
            "mensagem": "Você não tem mais acesso a essa triagem. Aguarde o feedback do seu Coordenador(a).",
        }
    else:
        context = {
            "paciente": triage.patient.nome_completo,
            "triage": triage,
           
            "pode_submeter": (
                request.user.role == Role.ALUNO
                and triage.student_author_id == request.user.pk
                and triage.is_open
            ),
            "pode_dar_feedback": TriageFeedback.can_be_created_by(request.user),
            "pode_encaminhar": Referral.can_be_created_by(request.user, triage=triage),
        }

    return render(request, "triage/triage_details.html", context)


@login_required
def create_feedback(request, pk):
    """Cria o parecer/feedback (Professor, herdado por Supervisor)."""
    triage = get_object_or_404(TriageRecord, pk=pk)

    if not TriageFeedback.can_be_created_by(request.user):
        return HttpResponseForbidden("Você não pode enviar parecer pra essa triagem.")

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            TriageFeedback.objects.create(
                triage=triage,
                author=request.user,
                content=content,
            )
            messages.success(request, "Parecer enviado.")
        else:
            messages.error(request, "O parecer não pode ficar em branco.")
        return redirect("triage_detail", pk=pk)

    return render(request, "triage/create_feedback.html", {"triage": triage})


@login_required
def create_referral(request, pk):
    if request.user.role != Role.SUPERVISOR:
        return HttpResponseForbidden("Vc não pode fazer o encaminhamento dessa triagem")

    referral_for_screening = get_object_or_404(TriageRecord, pk=pk)

    if not Referral.can_be_created_by(request.user, triage=referral_for_screening):
        return HttpResponseForbidden("Essa triagem ainda não foi submetida.")

    all_areas = AreaActing.objects.all()
    patient = referral_for_screening.patient
    # request.user é sempre CustomUser (AUTH_USER_MODEL), nunca a subclasse
   
    coordinator = get_object_or_404(Teacher, pk=request.user.pk)

    if request.method == "POST":
        area_ids = request.POST.getlist("areas")

        if not area_ids:
            context = {
                "all_areas": all_areas,
                "referral_for_screening": referral_for_screening,
                "erro": "Selecione 1 ou mais áreas de atuação",
            }
            return render(request, "triage/create_referral.html", context)

        areas_selecionadas = AreaActing.objects.filter(pk__in=area_ids)
        professores_da_area = Teacher.objects.filter(
            acting_areas__in=areas_selecionadas,
            role=Role.PROFESSOR,
        ).distinct()

        with transaction.atomic():
            referral_details = Referral.objects.create(
                triage=referral_for_screening,
                patient=patient,
                coordinator=coordinator,
            )
            referral_details.area.set(areas_selecionadas)
            # todo professor que atua em alguma das áreas escolhidas ganha
            
            patient.responsible_teachers.set(professores_da_area)

        
        return redirect("supervisor:orientacao")

    context = {
        "all_areas": all_areas,
        "referral_for_screening": referral_for_screening,
    }

    return render(request, "triage/create_referral.html", context)