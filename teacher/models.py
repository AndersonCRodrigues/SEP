from django.db import models
from core.models import CustomUser


class AreaAtuacao(models.Model):
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Abordagem/Área")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")

    class Meta:
        verbose_name = "Área de Atuação"
        verbose_name_plural = "Áreas de Atuação"

    def __str__(self):
        return self.nome


class PerfilProfessor(models.Model):
    usuario = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="perfil_professor",
        limit_choices_to={"role__in": [CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR]},
    )
    area_atuacao = models.ForeignKey(
        AreaAtuacao,
        on_delete=models.PROTECT,
        related_name="professores",
        verbose_name="Área de Atuação",
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Perfil de Professor/Supervisor"
        verbose_name_plural = "Perfis de Professores/Supervisores"

    def __str__(self):
        return f"{self.usuario.nome_completo} - {self.area_atuacao.nome}"