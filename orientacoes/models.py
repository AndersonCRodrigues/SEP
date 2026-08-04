from django.db import models, transaction
from core.models import CustomUser
from django.db.models import Q, UniqueConstraint
from django.utils import timezone
from django.core.exceptions import ValidationError


class AreaAtuacao(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nome

class OrientacaoManager(models.Manager):
    @transaction.atomic
    def trocar_orientador(self, aluno, novo_professor, area, periodo):
      
        orientacao_atual = self.select_for_update().filter(aluno=aluno, data_fim__isnull=True).first()

        if orientacao_atual:
            if orientacao_atual.professor == novo_professor:
                raise ValidationError(
                    "O aluno ja esta sendo orientado por este professor."
                )
            orientacao_atual.data_fim = timezone.now().date()
            orientacao_atual.save()

        return self.create(
            aluno=aluno,
            professor=novo_professor,
            area=area,
            periodo=periodo,
        )


class Orientacao(models.Model):
    aluno = models.ForeignKey(
        CustomUser, related_name="orientacoes", on_delete=models.PROTECT,
        limit_choices_to={"role": CustomUser.Role.ALUNO},
    )
    professor = models.ForeignKey(
        CustomUser, related_name="orientandos", on_delete=models.PROTECT,
        limit_choices_to={"role": CustomUser.Role.PROFESSOR},
    )
    area = models.ForeignKey(AreaAtuacao, on_delete=models.PROTECT)
    periodo = models.CharField(max_length=6)  # ex: "2026.1"

    data_inicio = models.DateField(auto_now_add=True)
    data_fim = models.DateField(null=True, blank=True)

    objects = OrientacaoManager()

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["aluno"],
                condition=Q(data_fim__isnull=True),
                name="aluno_com_no_maximo_uma_orientacao_ativa",
            )
        ]

    def __str__(self):
        status = "ativa" if self.data_fim is None else f"encerrada em {self.data_fim}"
        return f"{self.aluno} orientado por {self.professor} ({self.periodo}, {status})"
