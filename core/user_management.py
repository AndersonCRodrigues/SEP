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
    Role.SUPERADMIN: (Role.SUPERVISOR, Role.ADMIN),
    Role.SUPERVISOR: (Role.PROFESSOR, Role.ALUNO, Role.ADMIN),
}


def can_manage_user(actor, target_role):
    """Colunas Create e Delete: quais papeis o `actor` pode criar ou apagar."""
    if not actor.is_authenticated:
        return False
    return target_role in MANAGEABLE_ROLES_BY.get(actor.role, ())


def editable_user_fields(actor, target):
    """Coluna Update: campos que o `actor` pode gravar no usuario `target`."""
    if not actor.is_authenticated:
        return ()

    if actor.is_superuser or actor.role == Role.SUPERADMIN:
        return CustomUser.ALL_EDITABLE_FIELDS

    if actor.role == Role.SUPERVISOR and target.role in (Role.PROFESSOR, Role.ALUNO):
        return CustomUser.ALL_EDITABLE_FIELDS

    if actor.role == Role.PACIENTE and target.pk == actor.pk:
        return CustomUser.ADDRESS_FIELDS

    return ()
