from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet

Role = CustomUser.Role


class SecurityLogQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()
        if user.is_superuser or user.role == Role.SUPERADMIN:
            return self
        return self.none()

    def expired(self):
        limit = timezone.now() - timedelta(days=SecurityLog.RETENTION_DAYS)
        return self.filter(created_at__lt=limit)


class SecurityLog(BusinessRulesMixin, models.Model):
    """Trilha de auditoria, retida por 1 ano.

    A limpeza depende do comando `purge_security_logs` rodar periodicamente.
    """

    RETENTION_DAYS = 365

    class Action(models.TextChoices):
        LOGIN = "LI", "Login"
        LOGOUT = "LO", "Logout"
        LOGIN_FAILED = "LF", "Falha de login"
        CREATE = "CR", "Criação"
        UPDATE = "UP", "Alteração"
        DELETE = "DE", "Exclusão"
        ACCESS_DENIED = "AD", "Acesso negado"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="security_logs",
        verbose_name="Usuário",
    )

    # Texto e nao FK: o log precisa sobreviver a exclusao do usuario.
    user_identifier = models.CharField(
        max_length=254,
        blank=True,
        verbose_name="Identificação do usuário",
    )

    action = models.CharField(
        max_length=2,
        choices=Action.choices,
        verbose_name="Ação",
    )

    target_model = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Model alvo",
    )

    target_id = models.CharField(max_length=50, blank=True, verbose_name="ID alvo")

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Endereço IP",
    )

    detail = models.TextField(blank=True, verbose_name="Detalhe")

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name="Registrado em",
    )

    objects = SecurityLogQuerySet.as_manager()

    # Escrito pelos signals e removido apenas pela purga de retenção.
    CREATABLE_BY = ()
    EDITABLE_FIELDS = {}
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Log de segurança"
        verbose_name_plural = "Logs de segurança"
        ordering = ["-created_at"]

    def __str__(self):
        who = self.user_identifier or "anônimo"
        return f"{self.get_action_display()} por {who} em {self.created_at:%d/%m/%Y %H:%M}"
