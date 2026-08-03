from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from localflavor.br.models import BRCPFField,BRStateField,BRPostalCodeField
from .managers import CustomUserManager
from django.db.models import Q, UniqueConstraint
from django.utils import timezone


class CustomUser(AbstractUser):
    username=None
    email=models.EmailField(_("Adicionar email"),unique=True)
    
    nome_completo=models.CharField(max_length=350,verbose_name="Nome Completo")
    cpf = BRCPFField(unique=True,verbose_name="CPF")
    telefone = models.CharField(max_length=20,verbose_name="Telefone")
    
    logradouro = models.CharField(max_length=200,verbose_name="Logradouro")
    numero = models.CharField(max_length=10,verbose_name="Número")
    complemento = models.CharField(max_length=100,blank=True,verbose_name="Complemento")
    bairro = models.CharField(max_length=100,verbose_name="Bairro")
    cidade = models.CharField(max_length=100,verbose_name="Cidade")
    estado = BRStateField(verbose_name="Estado")
    cep = BRPostalCodeField(verbose_name="CEP")
    
    class Role(models.TextChoices):
            SUPERADMIN = "SA", _("Superadmin")
            SUPERVISOR = "SV", _("Supervisor Geral")
            PROFESSOR = "PR", _("Professor Responsável")
            ADMIN = "AD", _("Administrativo")
            ALUNO = "AL", _("Aluno")
        
    role = models.CharField(
        max_length=2,choices=Role.choices,default=Role.ALUNO,verbose_name="Cargo"
        )
    
    matricula = models.CharField(max_length=20,blank=True,verbose_name="Matricula")
    crp = models.CharField(max_length=15,blank=True,verbose_name='CRP')
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo","cpf"]
    
    objects = CustomUserManager()
    
    def clean(self):
        super().clean()
        if self.role == self.Role.ALUNO and not self.matricula:
            raise ValidationError({"Matricula":"Aluno precisa de matricula."})
        
        if self.role in(self.Role.PROFESSOR,self.Role.SUPERVISOR) and not self.crp:
            raise ValidationError({"CRP":"Professor/Supervisor precisa ter o crp"})
    
    def __str__(self):
        return f"{self.nome_completo} / {self.email}"
        
    
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = 'Usuários'

    
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

