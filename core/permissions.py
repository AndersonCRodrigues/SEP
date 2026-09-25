"""
Regras de CRUD por Role

A matriz opera em tres granularidades e so a primeira cabe no sistema nativo de
Permission do Django:

  1. model  -- "Supervisor: Read Todos"
  2. linha  -- "Professor: pacientes de seus alunos"   -> visible_to()
  3. campo  -- "Paciente: Update Endereco/telefone"    -> EDITABLE_FIELDS

Este modulo cobre os niveis 2 e 3. Role mora aqui, e nao em core.models, porque
CustomUser precisa importar daqui e o caminho inverso criaria ciclo.
"""

from django.db import models


class Role(models.TextChoices):
    SUPERADMIN = "SA"
    SUPERVISOR = "SV"
    PROFESSOR = "PR"
    ADMINISTRATIVO = "AD"
    ALUNO = "AL"
    PACIENTE = "PA"


INHERITS = {Role.SUPERVISOR: Role.PROFESSOR}
"""Papeis que acumulam os poderes de outro. Ler: o Supervisor faz tudo que o
Professor faz, e mais o que declarar em nome proprio."""


def roles_for(role):
    """O papel seguido dos que ele herda, do mais especifico ao mais generico."""
    cadeia = [role]
    enquanto = INHERITS.get(role)
    while enquanto is not None and enquanto not in cadeia:
        cadeia.append(enquanto)
        enquanto = INHERITS.get(enquanto)
    return tuple(cadeia)


ALL = "ALL"
"""Valor de VISIBLE_TO: o papel enxerga o queryset inteiro."""

ANY = "ANY"
"""Chave de VISIBLE_TO: vale para qualquer usuario autenticado."""


def effective_role(user):
    """Superusuario responde como Superadmin, tenha o role que tiver."""
    return Role.SUPERADMIN if user.is_superuser else user.role


class RoleScopedQuerySet(models.QuerySet):
    """
    Recorte por linha, declarado em VISIBLE_TO:

        {papel: ALL | callable(user) -> Q}

    Papel ausente nao enxerga nada. ANY como chave atende quem nao tem entrada
    propria. A cadeia de INHERITS vale aqui tambem, mas quase todo queryset
    declara o Supervisor explicitamente -- ele le mais que o Professor, nao o
    mesmo, e onde nao le (o log de auditoria) o silencio e proposital.
    """

    VISIBLE_TO = {}

    def scope_for(self, role):
        if not self.VISIBLE_TO:
            raise NotImplementedError(f"Declare VISIBLE_TO em {type(self).__name__}.")
        for papel in roles_for(role):
            if papel in self.VISIBLE_TO:
                return self.VISIBLE_TO[papel]
        return self.VISIBLE_TO.get(ANY)

    def readable_by_role(self, role):
        return self.scope_for(role) is not None

    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        escopo = self.scope_for(effective_role(user))
        if escopo is None:
            return self.none()
        if escopo is ALL:
            return self
        return self.filter(escopo(user)).distinct()


class BusinessRulesMixin:
    """
    Declara, por model, quem pode criar, quais campos cada papel escreve e
    quem pode apagar.

    CREATABLE_BY    -- papeis que podem criar
    EDITABLE_FIELDS -- {papel: (campos gravaveis)}; papel ausente nao edita nada
    DELETABLE_BY    -- papeis que podem apagar; vazio significa ninguem, que e
                       o default da matriz para todo model de conteudo

    Declare sempre pelo papel mais restrito: quem herda dele recebe junto, por
    INHERITS. Declarar o papel herdeiro tambem so faz sentido para ampliar.
    """

    CREATABLE_BY = ()
    EDITABLE_FIELDS = {}
    DELETABLE_BY = ()

    @classmethod
    def creatable_by_role(cls, role):
        return any(papel in cls.CREATABLE_BY for papel in roles_for(role))

    @classmethod
    def deletable_by_role(cls, role):
        return any(papel in cls.DELETABLE_BY for papel in roles_for(role))

    @classmethod
    def editable_fields_for_role(cls, role):
        campos = []
        for papel in roles_for(role):
            for campo in cls.EDITABLE_FIELDS.get(papel, ()):
                if campo not in campos:
                    campos.append(campo)
        return tuple(campos)

    @classmethod
    def can_be_created_by(cls, user, **context):
        if not user.is_authenticated:
            return False
        return cls.creatable_by_role(user.role)

    def editable_fields_for(self, user):
        """
        Campos que este usuario pode gravar NESTE objeto. Models com condicao
        por linha (ex.: so enquanto pendente) sobrescrevem este metodo.
        """
        if not user.is_authenticated:
            return ()
        return self.editable_fields_for_role(user.role)

    def can_be_changed_by(self, user):
        if not self.editable_fields_for(user):
            return False
        return type(self).objects.visible_to(user).filter(pk=self.pk).exists()

    def can_be_deleted_by(self, user):
        if not user.is_authenticated:
            return False
        return self.deletable_by_role(user.role)
