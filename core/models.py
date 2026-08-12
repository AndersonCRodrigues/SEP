from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from localflavor.br.models import BRCPFField,BRStateField,BRPostalCodeField
from .managers import CustomUserManager


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
        SUPERADMIN = "SA"
        SUPERVISOR = "SV"
        PROFESSOR = "PR"
        ADMINISTRATIVO = "AD"
        ALUNO = "AL"
        PACIENTE = "PA"

    role = models.CharField(
        max_length=2, choices=Role.choices, default=Role.ALUNO, verbose_name="Cargo"
    )

    matricula = models.CharField(max_length=20, blank=True, verbose_name="Matricula")
    crp = models.CharField(max_length=15, blank=True, verbose_name='CRP')

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo", "cpf"]

    objects = CustomUserManager()

    ADDRESS_FIELDS = (
        "telefone", "logradouro", "numero", "complemento",
        "bairro", "cidade", "estado", "cep",
    )
    ALL_EDITABLE_FIELDS = ("nome_completo", "email", "cpf", "role",
                           "matricula", "crp") + ADDRESS_FIELDS

    def clean(self):
        super().clean()
        if self.role in (self.Role.ALUNO, self.Role.ADMINISTRATIVO) and not self.matricula:
            raise ValidationError({"matricula": "Aluno e Administrativo precisam de matrícula."})

        if self.role in (self.Role.PROFESSOR, self.Role.SUPERVISOR) and not self.crp:
            raise ValidationError({"crp": "Professor/Supervisor precisa ter o CRP."})
    
    def __str__(self):
        return f"{self.nome_completo} / {self.email}"
        
    
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = 'Usuários'
