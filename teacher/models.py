from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from areas.models import AreaActing
from core.models import CustomUser


class Professor(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil_professor",
        verbose_name="Usuário",
    )

    area_atuacao = models.ForeignKey(
        AreaActing,
        on_delete=models.PROTECT,
        related_name="professores",
        verbose_name="Área de atuação",
    )

    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "Professores"

    def clean(self):
        super().clean()
        if self.usuario_id and self.usuario.role != CustomUser.Role.PROFESSOR:
            raise ValidationError(
                {
                    "usuario": "O usuário vinculado precisa ter o cargo Professor Responsável."
                }
            )

    def __str__(self):
        return f"{self.usuario.nome_completo} ({self.area_atuacao})"
