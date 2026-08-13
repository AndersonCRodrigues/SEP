from utils.fields import EncryptedFieldMixin
from .middleware import get_current_ip, get_current_user
from .models import SecurityLog

IGNORED_FIELDS = frozenset(
    {
        "created_at",
        "updated_at",
        "password",
        "last_login",
        "changes",
    }
)

SENSITIVE_FIELDS = frozenset(
    {
        "cpf",
        "telefone",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cidade",
        "estado",
        "cep",
        "content",
        "main_complaint",
        "notes",
        "detail",
    }
)


def _plain(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _value(instance, field):
    return getattr(instance, field.attname)


def _is_sensitive(field):
    return isinstance(field, EncryptedFieldMixin) or field.name in SENSITIVE_FIELDS


def auditable_fields(model):
    return [
        field
        for field in model._meta.concrete_fields
        if field.name not in IGNORED_FIELDS and not field.primary_key
    ]


def diff(previous, instance):
    changes = {}
    for field in auditable_fields(type(instance)):
        after = _value(instance, field)
        before = _value(previous, field) if previous is not None else None

        if previous is not None and before == after:
            continue

        if _is_sensitive(field):
            changes[field.name] = {"changed": True}
        else:
            changes[field.name] = {"old": _plain(before), "new": _plain(after)}
    return changes


def record(action, instance, changes=None, detail=""):
    user = get_current_user()
    return SecurityLog.objects.create(
        user=user,
        user_identifier=getattr(user, "email", "") or "",
        action=action,
        target_model=f"{instance._meta.app_label}.{type(instance).__name__}",
        target_id=str(instance.pk),
        changes=changes or {},
        detail=detail,
        ip_address=get_current_ip(),
    )


def log_export(instance, detail=""):
    return record(SecurityLog.Action.EXPORT, instance, detail=detail)


def log_access_denied(instance, detail=""):
    return record(SecurityLog.Action.ACCESS_DENIED, instance, detail=detail)
