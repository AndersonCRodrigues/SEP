from django.db import models

from core.models import CustomUser
from core.permissions import BusinessRulesMixin, RoleScopedQuerySet

Role = CustomUser.Role


class AreaActingQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()
        return self


class AreaActing(BusinessRulesMixin, models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome")

    objects = AreaActingQuerySet.as_manager()

    CREATABLE_BY = (Role.SUPERVISOR,)
    EDITABLE_FIELDS = {Role.SUPERVISOR: ("nome",)}
    DELETABLE_BY = (Role.SUPERVISOR,)

    class Meta:
        verbose_name = "Área de atuação"
        verbose_name_plural = "Áreas de atuação"
        ordering = ["nome"]

    def __str__(self):
        return self.nome
