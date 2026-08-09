from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import StudentActivity

ACTIVITY_KIND_BY_APPOINTMENT_KIND = {
    "TR": StudentActivity.Kind.SCREENING,
    "SE": StudentActivity.Kind.SESSION,
}


@receiver(post_save, sender="patient.Appointment")
def sync_student_activity(sender, instance, **kwargs):
    counts = (
        instance.status == sender.Status.ATTENDED
        and instance.assigned_student_id is not None
    )
    if not counts:
        StudentActivity.objects.filter(appointment=instance).delete()
        return

    StudentActivity.objects.update_or_create(
        appointment=instance,
        defaults={
            "student_id": instance.assigned_student_id,
            "date": timezone.localtime(instance.scheduled_at).date(),
            "kind": ACTIVITY_KIND_BY_APPOINTMENT_KIND[instance.kind],
            "minutes": instance.duration_minutes,
        },
    )
