from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from patient.models import Patient
from triage.models import TriageRecord
from .middleware import get_current_ip, get_current_user
from .models import AuditLog


AUDITED_MODELS = (
    Patient,
    TriageRecord,
)


def get_audit_actor():
    user = get_current_user()

    if user is None:
        return None

    if not getattr(user, "is_authenticated", False):
        return None

    return user


def get_changed_fields(sender, previous_instance, current_instance):
    changed_fields = []

    for field in sender._meta.concrete_fields:
        if field.primary_key:
            continue

        previous_value = getattr(
            previous_instance,
            field.attname,
        )

        current_value = getattr(
            current_instance,
            field.attname,
        )

        if previous_value != current_value:
            changed_fields.append(field.name)

    return changed_fields


@receiver(pre_save, sender=Patient)
@receiver(pre_save, sender=TriageRecord)
def capture_previous_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._audit_changed_fields = []
        return

    try:
        previous_instance = sender.objects.get(
            pk=instance.pk
        )
    except sender.DoesNotExist:
        instance._audit_changed_fields = []
        return

    instance._audit_changed_fields = get_changed_fields(
        sender,
        previous_instance,
        instance,
    )


@receiver(post_save, sender=Patient)
@receiver(post_save, sender=TriageRecord)
def create_or_update_audit_log(
    sender,
    instance,
    created,
    **kwargs,
):
    actor = get_audit_actor()
    ip_address = get_current_ip()

    if created:
        action = AuditLog.Action.CREATE

        changes = {
            "created": True,
        }

    else:
        changed_fields = getattr(
            instance,
            "_audit_changed_fields",
            [],
        )

        if not changed_fields:
            return

        action = AuditLog.Action.UPDATE

        changes = {
            field_name: {
                "changed": True,
            }
            for field_name in changed_fields
        }

    AuditLog.objects.create(
        actor=actor,
        action=action,
        model_name=sender.__name__,
        object_id=str(instance.pk),
        changes=changes,
        ip_address=ip_address,
    )

    if hasattr(instance, "_audit_changed_fields"):
        delattr(instance, "_audit_changed_fields")


@receiver(post_delete, sender=Patient)
@receiver(post_delete, sender=TriageRecord)
def delete_audit_log(
    sender,
    instance,
    **kwargs,
):
    AuditLog.objects.create(
        actor=get_audit_actor(),
        action=AuditLog.Action.DELETE,
        model_name=sender.__name__,
        object_id=str(instance.pk),
        changes={
            "deleted": True,
        },
        ip_address=get_current_ip(),
    )