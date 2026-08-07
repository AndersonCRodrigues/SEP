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
        # O tipo E o cargo: sob heranca multi-tabela nao faz sentido um Teacher
        # com role diferente de PROFESSOR, entao o campo nao fica a cargo de quem cria.
        self.role = CustomUser.Role.PROFESSOR
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome_completo} ({self.acting_area})"
