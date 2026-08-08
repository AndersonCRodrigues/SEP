"""
Regras de CRUD por papel, derivadas de docs/backend_roles/matriz-permissoes1.pdf.

A matriz opera em tres granularidades e so a primeira cabe no sistema nativo de
Permission do Django:

  1. model  -- "Supervisor: Read Todos"
  2. linha  -- "Professor: pacientes de seus alunos"   -> visible_to()
  3. campo  -- "Paciente: Update Endereco/telefone"    -> EDITABLE_FIELDS

Este modulo cobre os niveis 2 e 3. Nao importa nada de core.models de proposito:
CustomUser precisa importar daqui, e o caminho inverso criaria ciclo.
"""

from django.db import models


class RoleScopedQuerySet(models.QuerySet):
    def visible_to(self, user):
        raise NotImplementedError(
            "Defina visible_to() na subclasse de RoleScopedQuerySet."
        )


class BusinessRulesMixin:
    """
    Declara, por model, quem pode criar, quais campos cada papel escreve e
    quem pode apagar.

    CREATABLE_BY    -- papeis que podem criar
    EDITABLE_FIELDS -- {papel: (campos gravaveis)}; papel ausente nao edita nada
    DELETABLE_BY    -- papeis que podem apagar; vazio significa ninguem, que e
                       o default da matriz para todo model de conteudo
    """

    CREATABLE_BY = ()
    EDITABLE_FIELDS = {}
    DELETABLE_BY = ()

    @classmethod
    def editable_fields_for_role(cls, role):
        """Declaracao estatica: util para montar formularios de criacao."""
        return tuple(cls.EDITABLE_FIELDS.get(role, ()))

    @classmethod
    def can_be_created_by(cls, user, **context):
        if not user.is_authenticated:
            return False
        return user.role in cls.CREATABLE_BY

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
        # Ter campo gravavel nao basta: o objeto tambem precisa estar no escopo
        # de leitura do usuario.
        return type(self).objects.visible_to(user).filter(pk=self.pk).exists()

    def can_be_deleted_by(self, user):
        if not user.is_authenticated:
            return False
        return user.role in self.DELETABLE_BY
