from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

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


def get_iarv_form_class_for_instance(iarv):
    if isinstance(iarv, IarvChildForm.Meta.model):
        return IarvChildForm
    if isinstance(iarv, IarvAdolescentForm.Meta.model):
        return IarvAdolescentForm
    return IarvAdultForm


@login_required
def minhas_triagens(request):
    """
    Lista as triagens do próprio Aluno, pra ele conseguir voltar depois e
    ver o parecer do Supervisor
    """
    if request.user.role != Role.ALUNO:
        raise PermissionDenied("Apenas Alunos podem acessar as próprias triagens.")

    triagens = TriageRecord.objects.filter(student_author_id=request.user.pk).order_by(
        "-created_at"
    )

    return render(request, "triage/minhas_triagens.html", {"triagens": triagens})


@login_required
def triagem_concluida(request, pk):
    """Tela de confirmação exibida logo após o Aluno criar a ficha."""
    triage = get_object_or_404(TriageRecord, pk=pk)

    if triage.student_author_id != request.user.pk:
        raise PermissionDenied("Você não tem acesso a essa triagem.")

    return render(request, "triage/triagem_concluida.html", {"triage": triage})


@login_required
def fila_triagem(request):
    if request.user.role != Role.ALUNO:
        raise PermissionDenied("Apenas Alunos podem acessar a fila de triagem.")

    pacientes_aguardando = Patient.objects.awaiting_triage()

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
        raise PermissionDenied("Apenas alunos podem criar uma ficha de triagem.")

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

            return redirect("triagem_concluida", pk=triage_record.pk)

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
def edit_triage(request, pk):
    triage = get_object_or_404(TriageRecord, pk=pk)
    user = request.user

    is_dono_aluno = user.role == Role.ALUNO and triage.student_author_id == user.pk
    is_staff = user.role in [Role.SUPERVISOR, Role.PROFESSOR]

    if is_dono_aluno:
        if not triage.editable_fields_for(user):
            raise PermissionDenied("Essa triagem não pode mais ser editada pelo aluno.")
    elif is_staff:
        if not TriageRecord.objects.visible_to(user).filter(pk=triage.pk).exists():
            raise PermissionDenied("Você não tem permissão para editar esta triagem.")
    else:
        raise PermissionDenied("Você não tem acesso a essa triagem.")

    iarv = triage.get_iarv()
    iarv_form_class = (
        get_iarv_form_class_for_instance(iarv)
        if iarv
        else get_iarv_form_class(triage.patient)
    )

    if request.method == "POST":
        triage_form = TriageRecordForm(request.POST, instance=triage)
        iarv_form = iarv_form_class(request.POST, instance=iarv)

        if triage_form.is_valid() and iarv_form.is_valid():
            with transaction.atomic():
                triage_form.save()
                iarv_form.save()
            messages.success(request, "Triagem atualizada com sucesso.")

            if user.role == Role.ALUNO:
                return redirect("triage_detail_student", pk=pk)
            return redirect("triage_detail_supervisor", pk=pk)
    else:
        triage_form = TriageRecordForm(instance=triage)
        iarv_form = iarv_form_class(instance=iarv)

    context = {
        "triage": triage,
        "triage_form": triage_form,
        "iarv_form": iarv_form,
        "cancel_url": reverse(
            "triage_detail_student"
            if user.role == Role.ALUNO
            else "triage_detail_supervisor",
            args=[pk],
        ),
    }

    return render(request, "triage/edit_triage.html", context)


@login_required
def submit_triage(request, pk):
    """Aluno envia a própria triagem OPEN pro Supervisor (OPEN -> SUBMITTED)."""
    if request.user.role != Role.ALUNO:
        raise PermissionDenied("Apenas Alunos podem enviar a própria triagem.")

    triage = get_object_or_404(TriageRecord, pk=pk)

    try:
        with transaction.atomic():
            triage.submit(request.user)
        messages.success(request, "Triagem enviada pro Supervisor.")
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("triage_detail_student", pk=pk)


@login_required
def lock_triage_editing(request, pk):
    if request.user.role != Role.SUPERVISOR:
        raise PermissionDenied("Apenas a Coordenação pode fechar a edição da triagem.")

    triage = get_object_or_404(TriageRecord, pk=pk)
    try:
        with transaction.atomic():
            triage.finalize_edition(request.user)
        messages.success(request, "Aluno não pode editar mais essa triagem.")
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("triage_detail_supervisor", pk=pk)


@login_required
def triage_detail_student(request, pk):
    """View exclusiva para visualização do Aluno."""
    if request.user.role != Role.ALUNO:
        raise PermissionDenied("Apenas alunos podem acessar esta visão.")

    triage = get_object_or_404(TriageRecord, pk=pk)

    if triage.student_author_id != request.user.pk:
        raise PermissionDenied("Você não tem acesso a essa triagem.")

    triage.refresh_from_db()
    iarv = triage.get_iarv()

    # Prepara os formulários com os dados preenchidos e desabilita todos os inputs
    triage_form = TriageRecordForm(instance=triage)

    iarv_form = None
    if iarv:
        iarv_form_class = get_iarv_form_class_for_instance(iarv)
        iarv_form = iarv_form_class(instance=iarv)

    forms_to_disable = [triage_form]
    if iarv_form:
        forms_to_disable.append(iarv_form)

    for form in forms_to_disable:
        for field in form.fields.values():
            field.widget.attrs["disabled"] = "disabled"

    context = {
        "paciente": triage.patient.nome_completo,
        "triage": triage,
        "iarv": iarv,
        "triage_form": triage_form,
        "iarv_form": iarv_form,
        "pode_submeter": (
            triage.student_author_id == request.user.pk and triage.is_open
        ),
        "pode_editar": (
            triage.student_author_id == request.user.pk
            and bool(triage.editable_fields_for(request.user))
        ),
    }

    return render(request, "triage/triage_detail_student.html", context)


@login_required
def triage_detail_supervisor(request, pk):
    """View exclusiva para visualização do Supervisor/Professor."""
    if request.user.role not in [Role.SUPERVISOR, Role.PROFESSOR]:
        raise PermissionDenied(
            "Apenas supervisores ou professores podem acessar esta visão."
        )

    triage = get_object_or_404(TriageRecord, pk=pk)

    if not TriageRecord.objects.visible_to(request.user).filter(pk=triage.pk).exists():
        raise PermissionDenied("Você não tem acesso a essa triagem.")

    triage.refresh_from_db()
    iarv = triage.get_iarv()
    iarv_updated = iarv.updated_at if iarv and hasattr(iarv, "updated_at") else None

    pode_travar_edicao = (
        triage.status == TriageStatus.SUBMITTED and request.user.role == Role.SUPERVISOR
    )

    editada_pos_envio = False
    if pode_travar_edicao and triage.submitted_at:
        if triage.updated_at > triage.submitted_at:
            editada_pos_envio = True
        elif iarv_updated and iarv_updated > triage.submitted_at:
            editada_pos_envio = True

    context = {
        "paciente": triage.patient.nome_completo,
        "triage": triage,
        "iarv": iarv,
        "pode_editar": True,
        "pode_dar_feedback": TriageFeedback.can_be_created_by(request.user),
        "pode_encaminhar": Referral.can_be_created_by(request.user, triage=triage),
        "pode_travar_edicao": pode_travar_edicao,
        "triagem_editada_pos_envio": editada_pos_envio,
    }

    return render(request, "triage/triage_detail_supervisor.html", context)


@login_required
def create_feedback(request, pk):
    """Cria o parecer/feedback (Professor, herdado por Supervisor)."""
    triage = get_object_or_404(TriageRecord, pk=pk)

    if not TriageFeedback.can_be_created_by(request.user):
        raise PermissionDenied("Você não pode enviar parecer pra essa triagem.")

    if not TriageRecord.objects.visible_to(request.user).filter(pk=triage.pk).exists():
        raise PermissionDenied("Você não tem acesso a essa triagem.")

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
        return redirect("triage_detail_supervisor", pk=pk)

    return render(request, "triage/create_feedback.html", {"triage": triage})


@login_required
def create_referral(request, pk):
    if request.user.role != Role.SUPERVISOR:
        raise PermissionDenied("Você não pode fazer o encaminhamento dessa triagem.")

    referral_for_screening = get_object_or_404(TriageRecord, pk=pk)

    if not Referral.can_be_created_by(request.user, triage=referral_for_screening):
        raise PermissionDenied("Essa triagem ainda não foi submetida.")

    all_areas = AreaActing.objects.all()
    for area in all_areas:
        area.esta_ativa = area.teachers.filter(role=Role.PROFESSOR).exists()

    patient = referral_for_screening.patient
    coordinator = get_object_or_404(Teacher, pk=request.user.pk)

    if request.method == "POST":
        area_ids = request.POST.getlist("areas")

        if not area_ids:
            context = {
                "all_areas": all_areas,
                "referral_for_screening": referral_for_screening,
                "erro": "Selecione 1 ou mais áreas de atuação.",
            }
            return render(request, "triage/create_referral.html", context)

        areas_selecionadas = AreaActing.objects.filter(pk__in=area_ids)
        areas_com_professor = areas_selecionadas.filter(
            teachers__role=Role.PROFESSOR
        ).distinct()

        if areas_selecionadas.count() != areas_com_professor.count():
            context = {
                "all_areas": all_areas,
                "referral_for_screening": referral_for_screening,
                "erro": "Selecione apenas áreas ativas (com professores cadastrados).",
            }
            return render(request, "triage/create_referral.html", context)

        with transaction.atomic():
            triage_travada = TriageRecord.objects.select_for_update().get(
                pk=referral_for_screening.pk
            )
            if not Referral.can_be_created_by(request.user, triage=triage_travada):
                context = {
                    "all_areas": all_areas,
                    "referral_for_screening": triage_travada,
                    "erro": "Essa triagem já foi encaminhada.",
                }
                return render(request, "triage/create_referral.html", context)

            professores_da_area = Teacher.objects.filter(
                acting_areas__in=areas_selecionadas,
                role=Role.PROFESSOR,
            ).distinct()

            referral_details = Referral.objects.create(
                triage=triage_travada,
                patient=patient,
                coordinator=coordinator,
            )
            referral_details.area.set(areas_selecionadas)
            patient.responsible_teachers.set(professores_da_area)

        return redirect("supervisor:orientacao")

    context = {
        "all_areas": all_areas,
        "referral_for_screening": referral_for_screening,
    }

    return render(request, "triage/create_referral.html", context)
