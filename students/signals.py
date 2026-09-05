from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal

from .models import Advising, CaseAssignment, Student, StudentActivity

ACTIVITY_TYPE_BY_APPOINTMENT_KIND = {
    "TR": StudentActivity.ActivityType.SCREENING,
    "SE": StudentActivity.ActivityType.SESSION,
}

LINKED_FIELDS = ("current_advisor_id", "current_patient_id")

@receiver(post_save, sender="patient.Appointment")
def sync_student_activity(sender, instance, **kwargs):
    """Participacao conta pela ida do aluno; realizacao so quando o paciente veio."""
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

    with transaction.atomic():
        if previous["current_advisor_id"] != instance.current_advisor_id:
            Advising.objects.sync_from_student(instance, term=term)

        if previous["current_patient_id"] != instance.current_patient_id:
            CaseAssignment.objects.sync_from_student(instance)