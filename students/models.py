from django.db import models, transaction
from core.models import CustomUser
from teacher.models import Professor
from django.db.models import Q, UniqueConstraint
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


class Aluno(CustomUser):

    orientador_atual = models.ForeignKey(
        Professor,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="orientandos_atuais"
    )


class OrientacaoManager(models.Manager):
    @transaction.atomic
    def trocar_orientador(self, aluno, novo_professor, periodo):
      
        orientacao_atual = self.select_for_update().filter(aluno=aluno, data_fim__isnull=True).first()

        if orientacao_atual:
            if orientacao_atual.professor == novo_professor:
                raise ValidationError(
                    "O aluno ja esta sendo orientado por este professor."
                )
            orientacao_atual.data_fim = timezone.now().date()
            orientacao_atual.save()

        nova_orientacao = self.create(
        aluno=aluno,
        professor=novo_professor,
        periodo=periodo,
        )

        aluno.orientador_atual = novo_professor
        aluno.save(update_fields=["orientador_atual"])

        return nova_orientacao


class Orientacao(models.Model):
    aluno = models.ForeignKey(
        Aluno,
        related_name="historico_orientacoes",
        on_delete=models.PROTECT,
    )
    professor= models.ForeignKey(
        Professor, 
        related_name="historico_orientandos", 
        on_delete=models.PROTECT,
    )

    periodo = models.CharField(
        max_length=6,
        validators=[
            RegexValidator(
                regex=r"^\d{4}\.[12]$",
                message="O  período deve estar no formato AAAA.1 ou AAAA.2 (exemplo.:2026.1)."
            )
        ]
    )  # ex: "2026.1"

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
