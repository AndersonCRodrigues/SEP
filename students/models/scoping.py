"""Recortes de linha que mais de uma model do app reaproveita."""

from django.db.models import Q
from django.utils import timezone
from core.models import CustomUser
from core.permissions import RoleScopedQuerySet

Role = CustomUser.Role


def current_term(today=None):
    today = today or timezone.now().date()
    return f"{today.year}.{1 if today.month <= 6 else 2}"


def with_open_case(prefix="", **lookups):
    caminho = f"{prefix}assignment_history"
    filtros = {f"{caminho}__end_date__isnull": True}
    filtros.update({f"{caminho}__{campo}": valor for campo, valor in lookups.items()})
    return Q(**filtros)


def can_reach_student(user, student):
    if student is None:
        return False
    if user.role == Role.PROFESSOR:
        return student.current_advisor_id == user.pk
    return True


class AdviseeScopedQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if role == Role.SUPERVISOR:
            return self
        if role == Role.PROFESSOR:
            return self.filter(student__current_advisor_id=user.pk)
        if role == Role.ALUNO:
            return self.filter(student_id=user.pk)
        return self.none()
