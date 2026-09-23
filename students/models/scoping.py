from django.db.models import Q
from django.utils import timezone
from core.models import CustomUser
from core.permissions import ALL, RoleScopedQuerySet, effective_role, roles_for
from teacher.models import Teacher

Role = CustomUser.Role


def current_term(today=None):
    today = today or timezone.now().date()
    return f"{today.year}.{1 if today.month <= 6 else 2}"


def can_reach_student(user, student):
    if student is None:
        return False
    if user.role == Role.PROFESSOR:
        return student.current_advisor_id == user.pk
    return True


def advisees_visible_to(user):
    """Alunos que ``user`` enxerga como orientandos, considerando o papel.

    Regras confirmadas com produto (checkpoint de 16/09):
    - Professor e Supervisor usam a MESMA regra aqui: só os alunos onde
      ``current_advisor`` aponta pra ele mesmo -- o Supervisor também pode
      atuar como orientador direto, então nas telas do professor (Home,
      Meus Alunos, Presença, Triagem) ele só vê os próprios, igual a um
      Professor comum. "Ver todos os alunos do sistema" é regra exclusiva
      da tela de Usuários Cadastrados do Supervisor
      (supervisor.views.usuarios_alunos_e_professores), não desta função.
    - Além de ser orientador, a área de atuação do aluno (derivada do caso
      aberto -- ver Student.acting_area) precisa bater com uma das áreas
      de atuação do professor/supervisor. Um aluno sem nenhum caso aberto
      ainda não tem área nenhuma, então não aparece até que um
      CaseAssignment seja criado numa área em comum com o orientador.
    - Demais papéis: nenhum aluno.

    Centralizado aqui para ser reutilizado por qualquer view/queryset que
    precise da mesma regra (início, alunos, presença, triagem, etc.), em
    vez de cada uma reimplementar ``professor.current_advisees.all()``.
    """
    from .student import Student

    if not user.is_authenticated:
        return Student.objects.none()

    papeis = roles_for(effective_role(user))
    if Role.SUPERVISOR not in papeis and Role.PROFESSOR not in papeis:
        return Student.objects.none()

    professor = Teacher.objects.filter(pk=user.pk).first()
    if professor is None:
        return Student.objects.none()

    return Student.objects.filter(
        current_advisor_id=user.pk,
        case_history__end_date__isnull=True,
        case_history__acting_area__in=professor.acting_areas.all(),
    ).distinct()


class AdviseeScopedQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {
        Role.SUPERVISOR: ALL,
        Role.PROFESSOR: lambda u: Q(student__current_advisor_id=u.pk),
        Role.ALUNO: lambda u: Q(student_id=u.pk),
    }
