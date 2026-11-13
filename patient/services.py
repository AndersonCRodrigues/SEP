import hashlib
import secrets
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
import logging
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from patient.models.patient import FirstAcess, Patient
from audit.models import SecurityLog

logger = logging.getLogger(__name__)

sms_test_outbox = []
def build_first_access_url(token):
    base_url = settings.FIRST_ACCESS_BASE_URL.rstrip("/")

    access_path = reverse("patient:primeiro_acesso",kwargs={"token": token})

    return f"{base_url}{access_path}"

@transaction.atomic
def create_first_access_invitation(patient):
    validity_minutes = settings.FIRST_ACCESS_TOKEN_TIMEOUT_MINUTES

    if validity_minutes <= 0:
        raise ValueError("A validade deve ser maior que zero.")

    patient = Patient.objects.select_for_update().get(pk=patient.pk)

    now = timezone.now()

    FirstAcess.objects.filter(patient=patient, used_at__isnull=True, revoked_at__isnull=True,).update(revoked_at=now)

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    invitation = FirstAcess.objects.create(patient=patient, token_hash=token_hash, expires_at=now + timedelta(minutes=validity_minutes))
    return invitation, token

def validate_first_access_invitation(token, *, for_update=False):
    if not isinstance(token, str) or not token:
        raise ValidationError("Link inválido.")

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    invitations = FirstAcess.objects.all()

    if for_update:
        invitations = invitations.select_for_update()

    try:
        invitation = invitations.get(token_hash=token_hash)
    except FirstAcess.DoesNotExist:
        raise ValidationError("Link inválido.")

    if invitation.revoked_at is not None:
        raise ValidationError("Este link foi cancelado")

    if invitation.used_at is not None:
        raise ValidationError("Este link já foi utilizado")

    if timezone.now() >= invitation.expires_at:
        raise ValidationError("Este link expirou. Solicite um novo link de acesso.")

    return invitation

@transaction.atomic
def set_first_access_password(token, password, password_confirmation):
    if password != password_confirmation:
        raise ValidationError("As senhas dos campos não coincidem.")

    invitation = validate_first_access_invitation(token)

    patient = Patient.objects.select_for_update().get(
        pk=invitation.patient_id
    )

    invitation = validate_first_access_invitation(
        token,
        for_update=True,
    )

    validate_password(password, user=patient)

    patient.set_password(password)
    patient.must_change_password = False
    patient.save(update_fields=["password", "must_change_password"])

    invitation.used_at = timezone.now()
    invitation.save(update_fields=["used_at"])
    FirstAcess.objects.filter(patient=patient, used_at__isnull=True, revoked_at__isnull=True,).update(revoked_at=timezone.now())

    return patient

# uso com dados mockados nenhum sms real é enviado
@transaction.atomic
def deliver_first_access_sms(invitation, access_url,responsible_user=None,):
    if not settings.DEBUG:
        raise ImproperlyConfigured("O simulador de SMS só pode ser usado em desenvolvimento.")

    patient = invitation.patient

    if not patient.telefone:
        invitation.delivery_status = FirstAcess.DeliveryStatus.PENDING
        detail = "Primeiro acesso pendente: paciente sem telefone."
        message = None
    else:
        message = (
            "SEP: crie sua senha pelo link: "
            f"{access_url}"
        )

        invitation.delivery_status = FirstAcess.DeliveryStatus.SIMULATED
        detail = ("Mensagem de primeiro acesso preparada no simulador. ""Nenhum SMS real foi enviado.")

    invitation.save(update_fields=["delivery_status"])

    SecurityLog.objects.create(
        user=responsible_user or patient,
        user_identifier=(
            (responsible_user or patient).email
            or f"user:{(responsible_user or patient).pk}"
        ),
        action=SecurityLog.Action.CREATE,
        detail=detail,
        target_model=(
            f"{patient._meta.app_label}.{type(patient).__name__}"
        ),
        target_id=str(patient.pk)
    )

    if message is not None:
        transaction.on_commit(
            lambda: sms_test_outbox.append({"invitation_id": invitation.pk, "to": patient.telefone,"message": message}))

    return invitation.delivery_status

def send_first_access_sms(invitation,access_url,responsible_user=None):
    try:
        return deliver_first_access_sms(invitation=invitation, access_url=access_url, responsible_user=responsible_user)
    except Exception as error:
        logger.error("Falha no envio do convite %s. Tipo: %s", invitation.pk, type(error).__name__)

        try:
            FirstAcess.objects.filter(pk=invitation.pk).update(
                delivery_status=FirstAcess.DeliveryStatus.FAILED,
            )
        except Exception as status_error:
            logger.error(
                "Não foi possível registrar a falha do convite %s. Tipo: %s", invitation.pk, type(status_error).__name__)

        return FirstAcess.DeliveryStatus.FAILED

@transaction.atomic
def reissue_first_access_invitation(patient, responsible_user):
    patient = Patient.objects.select_for_update().get(pk=patient.pk)

    if patient.has_usable_password():
        raise ValidationError("Esta conta já possui uma senha ")

    invitation, token = create_first_access_invitation(patient)

    access_url = build_first_access_url(token)

    def send_after_commit():
        send_first_access_sms(invitation=invitation, access_url=access_url, responsible_user=responsible_user,)
        
    transaction.on_commit(send_after_commit)

    return invitation