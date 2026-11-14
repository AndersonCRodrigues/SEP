from django.db import models
from django.db.models import Case, Value, When
from core.models import CustomUser


class ServerStatusQuerySet(models.QuerySet):
    def with_alert(self):
        Health = self.model.Health
        return self.filter(health__in=(Health.OFFLINE, Health.ATENCAO)).order_by(
            Case(When(health=Health.OFFLINE, then=Value(0)), default=Value(1)),
            "nome",
        )


class ServerStatus(models.Model):
    class Health(models.TextChoices):
        SAUDAVEL = "OK", "Saudável"
        ATENCAO = "AT", "Atenção"
        OFFLINE = "OF", "Indisponível"

    CPU_LIMIT_PERCENT = 80
    MEMORY_LIMIT_PERCENT = 85

    nome = models.CharField(max_length=100, verbose_name="Servidor")
    uptime_percent = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name="Uptime (%)"
    )
    cpu_percent = models.PositiveSmallIntegerField(verbose_name="CPU (%)")
    memoria_percent = models.PositiveSmallIntegerField(verbose_name="Memória (%)")
    health = models.CharField(
        max_length=2, choices=Health.choices, default=Health.SAUDAVEL
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    objects = ServerStatusQuerySet.as_manager()

    class Meta:
        verbose_name = "Status de servidor"
        verbose_name_plural = "Status de servidores"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.get_health_display()})"

    def metrics_over_limit(self):
        metrics = (
            ("CPU", self.cpu_percent, self.CPU_LIMIT_PERCENT),
            ("Memória", self.memoria_percent, self.MEMORY_LIMIT_PERCENT),
        )
        return [(name, value) for name, value, limit in metrics if value > limit]

    def alert_message(self):
        if self.health == self.Health.OFFLINE:
            return f"{self.nome} indisponível, sem resposta."
        exceeded = self.metrics_over_limit()
        if not exceeded:
            return f"{self.nome} em atenção."
        causes = " e ".join(f"{name} em {value}%" for name, value in exceeded)
        return f"{causes} no {self.nome}"


class RolePermissionScope(models.Model):
    role = models.CharField(
        max_length=2,
        choices=CustomUser.Role.choices,
        unique=True,
        verbose_name="Perfil",
    )
    escopo_acesso = models.CharField(max_length=255, verbose_name="Escopo de acesso")
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Escopo de permissão por perfil"
        verbose_name_plural = "Escopos de permissão por perfil"

    def __str__(self):
        return f"{self.get_role_display()} — {self.escopo_acesso}"


class BackupRecord(models.Model):
    class Status(models.TextChoices):
        CONCLUIDO = "OK", "Concluído"
        AGENDADO = "AG", "Agendado"
        FALHOU = "ER", "Falhou"

    escopo = models.CharField(max_length=100, verbose_name="Escopo")
    tamanho = models.CharField(max_length=20, blank=True, verbose_name="Tamanho")
    status = models.CharField(
        max_length=2, choices=Status.choices, default=Status.AGENDADO
    )
    executado_em = models.DateTimeField(null=True, blank=True)
    agendado_para = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Registro de backup"
        verbose_name_plural = "Registros de backup"
        ordering = ["-executado_em", "-agendado_para"]

    def __str__(self):
        return f"{self.escopo} ({self.get_status_display()})"
