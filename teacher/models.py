from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from areas.models import AreaActing
from core.models import CustomUser


class Teacher(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_profile",
        verbose_name="Usuário",
    )

    acting_area = models.ForeignKey(
        AreaActing,
        on_delete=models.PROTECT,
        related_name="teachers",
        verbose_name="Área de atuação",
    )

    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "Professores"

    def clean(self):
        super().clean()
        if self.user_id and self.user.role != CustomUser.Role.PROFESSOR:
            raise ValidationError(
                {
                    "user": "O usuário vinculado precisa ter o cargo Professor Responsável."
                }
            )

    def __str__(self):
        return f"{self.user.nome_completo} ({self.acting_area})"
