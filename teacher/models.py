from django.db import models
from areas.models import AreaActing
from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet

Role = CustomUser.Role


class ProfessorAreaQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()
        return self


class Teacher(CustomUser):
    acting_area = models.ForeignKey(
        AreaActing,
        on_delete=models.PROTECT,
        related_name="teachers",
        verbose_name="Área de atuação principal",
    )

    class Meta:
        verbose_name = "Professor"
        verbose_name_plural = "Professores"

    def save(self, *args, **kwargs):
        if self.role not in (CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR):
            self.role = CustomUser.Role.PROFESSOR
        super().save(*args, **kwargs)
        ProfessorArea.objects.get_or_create(professor=self, area=self.acting_area)

    def __str__(self):
        return f"{self.nome_completo} ({self.acting_area})"


class ProfessorArea(BusinessRulesMixin, models.Model):
    professor = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="professor_areas",
        verbose_name="Professor",
    )

    area = models.ForeignKey(
        AreaActing,
        on_delete=models.PROTECT,
        related_name="professor_areas",
        verbose_name="Área de atuação",
    )

    objects = ProfessorAreaQuerySet.as_manager()

    CREATABLE_BY = (Role.SUPERVISOR,)
    EDITABLE_FIELDS = {
        Role.SUPERVISOR: ("professor", "area"),
    }
    DELETABLE_BY = (Role.SUPERVISOR,)

    class Meta:
        verbose_name = "Professor Area"
        verbose_name_plural = "Professor Areas"
        constraints = [
            models.UniqueConstraint(
                fields=["professor", "area"],
                name="unique_professor_area",
            ),
        ]

    def __str__(self):
        return f"{self.professor} - {self.area}"
