from django.db.models import Q
from django.utils import timezone
from core.models import CustomUser
from core.permissions import ALL, RoleScopedQuerySet

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
    VISIBLE_TO = {
        Role.SUPERVISOR: ALL,
        Role.PROFESSOR: lambda u: Q(student__current_advisor_id=u.pk),
        Role.ALUNO: lambda u: Q(student_id=u.pk),
    }
