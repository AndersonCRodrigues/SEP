from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint
from areas.models import AreaActing
from core.models import CustomUser


class TeacherArea(models.Model):
    teacher = models.ForeignKey(
        "teacher.Teacher", on_delete=models.CASCADE, related_name="area_links"
    )
    area = models.ForeignKey(
        AreaActing, on_delete=models.PROTECT, related_name="teacher_links"
    )

    class Meta:
        verbose_name = "Atuação do professor"
        verbose_name_plural = "Atuações do professor"
        constraints = [
            UniqueConstraint(fields=["teacher", "area"], name="teacher_area_unica")
        ]


    def save(self, *args, **kwargs):
        if self.role not in (CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR):
            self.role = CustomUser.Role.PROFESSOR
        super().save(*args, **kwargs)


class Teacher(CustomUser):
    acting_areas = models.ManyToManyField(
        AreaActing,
        through=TeacherArea,
        related_name="teachers",
        verbose_name="Áreas de atuação",
    )

    def clean(self):
        super().clean()
        if self.pk and not self.acting_areas.exists():
            raise ValidationError(
                {"acting_areas": "Professor precisa de ao menos uma área de atuação."}
            )


    def __str__(self):
        areas = ", ".join(a.nome for a in self.acting_areas.all())
        return f"{self.nome_completo} ({areas})" if areas else self.nome_completo
