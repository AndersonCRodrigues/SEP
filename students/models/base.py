from django.db import models
from core.models import CustomUser
from core.permissions import BusinessRulesMixin
from .scoping import AdviseeScopedQuerySet, can_reach_student
from .student import Student

Role = CustomUser.Role


class AdviseeRecord(BusinessRulesMixin, models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.PROTECT,
        related_name="%(class)s_set",
        verbose_name="Aluno",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    objects = AdviseeScopedQuerySet.as_manager()

    CREATABLE_BY = (Role.PROFESSOR,)
    DELETABLE_BY = (Role.PROFESSOR,)

    class Meta:
        abstract = True

    @classmethod
    def can_be_created_by(cls, user, student=None, **context):
        if not super().can_be_created_by(user):
            return False
        return can_reach_student(user, student)
