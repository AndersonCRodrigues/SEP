"""
Gestao de usuarios

Vive fora dos models de proposito. As regras desta tabela sao chaveadas pelo
PAPEL DO ALVO ("Supervisor cria Professor / Aluno"), formato diferente das outras
seis tabelas da matriz, que sao chaveadas pelo objeto.

Manter isto como metodo de CustomUser fazia toda subclasse de heranca multi-tabela
-- Teacher, Student e Patient -- herdar poder de administrar usuarios sem declarar
nada, e o unico jeito de sair era reescrever os metodos na subclasse.
"""

from core.models import CustomUser

Role = CustomUser.Role


MANAGEABLE_ROLES_BY = {
    Role.SUPERADMIN: (Role.SUPERVISOR, Role.ADMINISTRATIVO),
    Role.SUPERVISOR: (Role.PROFESSOR, Role.ALUNO),
}


def can_manage_user(actor, target_role):
    """Colunas Create e Delete: quais papeis o `actor` pode criar ou apagar."""
    if not actor.is_authenticated:
        return False
    role = Role.SUPERADMIN if actor.is_superuser else actor.role
    return target_role in MANAGEABLE_ROLES_BY.get(role, ())


def target_fields(target):
    """Campos que so existem na subclasse, fora de ALL_EDITABLE_FIELDS."""
    campos = CustomUser.ALL_EDITABLE_FIELDS
    if target.role == Role.ALUNO:
        campos += ("stage",)
    if target.role in (Role.PROFESSOR, Role.SUPERVISOR):
        campos += ("acting_areas",)
    return campos


def editable_user_fields(actor, target):
    """Coluna Update: campos que o `actor` pode gravar no usuario `target`."""
    if not actor.is_authenticated:
        return ()

    if actor.is_superuser or actor.role == Role.SUPERADMIN:
        return target_fields(target)

    if actor.role == Role.SUPERVISOR and target.role in (Role.PROFESSOR, Role.ALUNO):
        return target_fields(target)

    if actor.role == Role.PROFESSOR and target.role == Role.ALUNO:
        orientando = getattr(target, "current_advisor_id", None) == actor.pk
        return ("stage",) if orientando else ()

    if actor.role == Role.PACIENTE and target.pk == actor.pk:
        return CustomUser.ADDRESS_FIELDS

    return ()
