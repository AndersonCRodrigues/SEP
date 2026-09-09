from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import UniqueConstraint
from areas.models import AreaActing
from core.models import CustomUser
from core.permissions import ALL, ANY, BusinessRulesMixin, RoleScopedQuerySet

Role = CustomUser.Role


class TeacherAreaQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {ANY: ALL}


class TeacherArea(BusinessRulesMixin, models.Model):
    teacher = models.ForeignKey(
        "teacher.Teacher",
        on_delete=models.CASCADE,
        related_name="area_links",
        verbose_name="Professor",
    )

    area = models.ForeignKey(
        AreaActing,
        on_delete=models.PROTECT,
        related_name="teacher_links",
        verbose_name="Área de atuação",
    )

    objects = TeacherAreaQuerySet.as_manager()

    CREATABLE_BY = (Role.SUPERVISOR,)
    EDITABLE_FIELDS = {Role.SUPERVISOR: ("teacher", "area")}
    DELETABLE_BY = (Role.SUPERVISOR,)

    class Meta:
        verbose_name = "Atuação do professor"
        verbose_name_plural = "Atuações do professor"
        constraints = [
            UniqueConstraint(fields=["teacher", "area"], name="teacher_area_unica")
        ]

    def __str__(self):
        return f"{self.teacher} - {self.area}"


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

    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "Professores"

    def enforce_role(self):
        if self.role not in (CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR):
            self.role = CustomUser.Role.PROFESSOR

    def clean(self):
        super().clean()
        if self.pk and not self.acting_areas.exists():
            raise ValidationError(
                {"acting_areas": "Professor precisa de ao menos uma área de atuação."}
            )


    def __str__(self):
        areas = ", ".join(a.nome for a in self.acting_areas.all())
        return f"{self.nome_completo} ({areas})" if areas else self.nome_completo
