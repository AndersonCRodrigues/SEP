from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

from .models import SecurityLog


def _client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    SecurityLog.objects.create(
        user=user,
        user_identifier=user.email,
        action=SecurityLog.Action.LOGIN,
        ip_address=_client_ip(request),
    )


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if user is None:
        return
    SecurityLog.objects.create(
        user=user,
        user_identifier=user.email,
        action=SecurityLog.Action.LOGOUT,
        ip_address=_client_ip(request),
    )


@receiver(user_login_failed)
def log_login_failed(sender, credentials, request=None, **kwargs):
    SecurityLog.objects.create(
        user=None,
        user_identifier=(credentials or {}).get("username", "") or "",
        action=SecurityLog.Action.LOGIN_FAILED,
        ip_address=_client_ip(request),
    )
