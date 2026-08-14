from django.db import models
from areas.models import AreaActing
from core.models import CustomUser


class Teacher(CustomUser):
    acting_area = models.ForeignKey(
        AreaActing,
        on_delete=models.PROTECT,
        related_name="teachers",
        verbose_name="Área de atuação",
    )

    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "Professores"

    def save(self, *args, **kwargs):
        self.role = CustomUser.Role.PROFESSOR
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome_completo} ({self.acting_area})"
