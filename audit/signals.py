from django.apps import apps
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from core.models import CustomUser
from core.permissions import BusinessRulesMixin

from .middleware import client_ip
from .models import SecurityLog
from .recording import diff, record


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    SecurityLog.objects.create(
        user=user,
        user_identifier=user.email,
        action=SecurityLog.Action.LOGIN,
        ip_address=client_ip(request),
    )


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if user is None:
        return
    SecurityLog.objects.create(
        user=user,
        user_identifier=user.email,
        action=SecurityLog.Action.LOGOUT,
        ip_address=client_ip(request),
    )


@receiver(user_login_failed)
def log_login_failed(sender, credentials, request=None, **kwargs):
    SecurityLog.objects.create(
        user=None,
        user_identifier=(credentials or {}).get("username", "") or "",
        action=SecurityLog.Action.LOGIN_FAILED,
        ip_address=client_ip(request),
    )


def audited_models():
    return [
        model
        for model in apps.get_models()
        if model is not SecurityLog
        and issubclass(model, (BusinessRulesMixin, CustomUser))
    ]


def capture_previous(sender, instance, **kwargs):
    instance._audit_previous = (
        sender._default_manager.filter(pk=instance.pk).first() if instance.pk else None
    )


def log_write(sender, instance, created, **kwargs):
    changes = diff(getattr(instance, "_audit_previous", None), instance)

    if created:
        record(SecurityLog.Action.CREATE, instance, changes)
        return

    if not changes:
        return

    action = (
        SecurityLog.Action.ROLE_CHANGE
        if "role" in changes
        else SecurityLog.Action.UPDATE
    )
    record(action, instance, changes)


def log_delete(sender, instance, **kwargs):
    record(SecurityLog.Action.DELETE, instance)


def log_permission_change(sender, instance, action, pk_set, **kwargs):
    if action not in ("post_add", "post_remove", "post_clear"):
        return
    record(
        SecurityLog.Action.PERMISSION_CHANGE,
        instance,
        {"action": action, "ids": sorted(pk_set) if pk_set else []},
    )


def connect():
    for model in audited_models():
        uid = model._meta.label_lower
        pre_save.connect(
            capture_previous, sender=model, dispatch_uid=f"audit_pre_{uid}"
        )
        post_save.connect(log_write, sender=model, dispatch_uid=f"audit_post_{uid}")
        post_delete.connect(log_delete, sender=model, dispatch_uid=f"audit_del_{uid}")

    for through in (CustomUser.groups.through, CustomUser.user_permissions.through):
        m2m_changed.connect(
            log_permission_change,
            sender=through,
            dispatch_uid=f"audit_m2m_{through._meta.label_lower}",
        )
