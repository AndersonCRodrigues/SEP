from django.db import models
from core.models import CustomUser


class ServerStatus(models.Model):
    class Health(models.TextChoices):
        SAUDAVEL = "OK", "Saudável"
        ATENCAO = "AT", "Atenção"
        OFFLINE = "OF", "Indisponível"

    nome = models.CharField(max_length=100, verbose_name="Servidor")
    uptime_percent = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Uptime (%)")
    cpu_percent = models.PositiveSmallIntegerField(verbose_name="CPU (%)")
    memoria_percent = models.PositiveSmallIntegerField(verbose_name="Memória (%)")
    health = models.CharField(max_length=2, choices=Health.choices, default=Health.SAUDAVEL)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Status de servidor"
        verbose_name_plural = "Status de servidores"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.get_health_display()})"


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
    status = models.CharField(max_length=2, choices=Status.choices, default=Status.AGENDADO)
    executado_em = models.DateTimeField(null=True, blank=True)
    agendado_para = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Registro de backup"
        verbose_name_plural = "Registros de backup"
        ordering = ["-executado_em", "-agendado_para"]

    def __str__(self):
        return f"{self.escopo} ({self.get_status_display()})"