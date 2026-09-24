from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

from django.db.models import Count
from core.models import CustomUser
from .models import Advising, CaseAssignment, Student, StudentActivity, current_term

ACTIVITY_TYPE_BY_APPOINTMENT_KIND = {
    "TR": StudentActivity.ActivityType.SCREENING,
    "SE": StudentActivity.ActivityType.SESSION,
}

LINKED_FIELDS = ("current_advisor_id",)


@receiver(post_save, sender="scheduling.Appointment")
def sync_student_activity(sender, instance, **kwargs):
    Category = StudentActivity.Category

    compareceu = instance.status in (
        sender.Status.ATTENDED,
        sender.Status.PATIENT_NO_SHOW,
    )
    responsavel_id = instance.teacher_id or getattr(
        instance.assigned_student, "current_advisor_id", None
    )

    if not (compareceu and instance.assigned_student_id and responsavel_id):
        StudentActivity.objects.filter(appointment=instance).delete()
        return

    devidas = {Category.PARTICIPATION: StudentActivity.PARTICIPATION_HOURS}
    if instance.status == sender.Status.ATTENDED:
        devidas[Category.EXECUTION] = Decimal(instance.duration_minutes) / Decimal(60)

    comum = {
        "student_id": instance.assigned_student_id,
        "date": timezone.localtime(instance.scheduled_at).date(),
        "activity_type": ACTIVITY_TYPE_BY_APPOINTMENT_KIND[instance.kind],
        "responsible_supervisor_id": responsavel_id,
    }

    with transaction.atomic():
        StudentActivity.objects.filter(appointment=instance).exclude(
            category__in=devidas
        ).delete()

        for categoria, horas in devidas.items():
            StudentActivity.objects.update_or_create(
                appointment=instance,
                category=categoria,
                defaults={**comum, "hours_worked": horas},
            )


@receiver(pre_save, sender=Student)
def capture_previous_links(sender, instance, **kwargs):
    stored = (
        Student.objects.filter(pk=instance.pk).values(*LINKED_FIELDS).first()
        if instance.pk
        else None
    )
    instance._previous_links = stored or dict.fromkeys(LINKED_FIELDS)


@receiver(post_save, sender=Student)
def sync_link_history(sender, instance, **kwargs):
    previous = getattr(instance, "_previous_links", None)
    if previous is None:
        return

    del instance._previous_links
    term = instance.__dict__.pop("_advising_term", None)

    if previous["current_advisor_id"] != instance.current_advisor_id:
        with transaction.atomic():
            Advising.objects.sync_from_student(instance, term=term)


@receiver(post_save, sender=CaseAssignment)
def vincular_professor_por_area(sender, instance, created, **kwargs):
    """Regra pedida por produto (checkpoint de 16/09): quando um aluno
    recebe uma área de atuação, ele vira instantaneamente orientando de um
    professor que atue nessa mesma área.

    CaseAssignment é o único lugar do sistema onde um aluno "recebe" uma
    área hoje -- Student não tem campo de área próprio, só a property
    `acting_area`, derivada do caso aberto (ver students/models/student.py).
    Por isso o gatilho é aqui, e não em Student.

    Duas suposições assumidas, para confirmar com produto se estiverem
    erradas:
    1. Só age se o aluno AINDA NÃO tem orientador -- não troca quem já foi
       vinculado a outro professor. Se a regra é sempre sobrescrever,
       remover o "if aluno.current_advisor_id is not None: return" abaixo.
    2. Se mais de um professor atua na mesma área, escolhe o que tem menos
       orientandos no momento (balanceamento simples). Se a regra é outra
       (ex.: sempre o mais antigo, sempre aleatório), trocar o
       .annotate/.order_by abaixo.
    """
    if not created or instance.end_date is not None:
        return

    aluno = instance.student
    if aluno.current_advisor_id is not None:
        return

    from teacher.models import Teacher

    professor = (
        Teacher.objects.filter(
            acting_areas=instance.acting_area,
            role__in=(CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR),
        )
        .annotate(qtd_orientandos=Count("current_advisees"))
        .order_by("qtd_orientandos", "pk")
        .first()
    )
    if professor is None:
        return

    Advising.objects.change_advisor(aluno, professor, term=current_term())
