from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from localflavor.br.models import BRCPFField,BRStateField,BRPostalCodeField
from .managers import CustomUserManager
from .permissions import BusinessRulesMixin, RoleScopedQuerySet


class CustomUserQuerySet(RoleScopedQuerySet):
    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        role = user.role
        if user.is_superuser or role == CustomUser.Role.SUPERADMIN:
            return self
        if role == CustomUser.Role.SUPERVISOR:
            # "Todos exceto Superadmin/Supervisor"
            return self.exclude(
                role__in=[CustomUser.Role.SUPERADMIN, CustomUser.Role.SUPERVISOR]
            )
        if role == CustomUser.Role.PROFESSOR:
            # "So seus Alunos orientandos". O acessor reverso da heranca
            # multi-tabela e 'student', e a PK do Student e a do proprio usuario.
            return self.filter(student__current_advisor_id=user.pk)
        if role == CustomUser.Role.ADMIN:
            return self.filter(
                role__in=[CustomUser.Role.ALUNO, CustomUser.Role.PACIENTE]
            )
        return self.filter(pk=user.pk)


class CustomUser(BusinessRulesMixin, AbstractUser):
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
            PACIENTE = "PA", _("Paciente")
        
    role = models.CharField(
        max_length=2,choices=Role.choices,default=Role.ALUNO,verbose_name="Cargo"
        )
    
    matricula = models.CharField(max_length=20,blank=True,verbose_name="Matricula")
    crp = models.CharField(max_length=15,blank=True,verbose_name='CRP')
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo","cpf"]

    # from_queryset preserva create_user/create_superuser, que o createsuperuser
    # e o admin dependem, e acrescenta o visible_to().
    objects = CustomUserManager.from_queryset(CustomUserQuerySet)()

    ADDRESS_FIELDS = (
        "telefone", "logradouro", "numero", "complemento",
        "bairro", "cidade", "estado", "cep",
    )
    ALL_EDITABLE_FIELDS = ("nome_completo", "email", "cpf", "role",
                           "matricula", "crp") + ADDRESS_FIELDS

    # Quem cria/apaga depende do papel do ALVO, nao so do autor -- por isso
    # estes mapas em vez do CREATABLE_BY/DELETABLE_BY generico.
    MANAGEABLE_ROLES_BY = {
        "SA": ("SV", "AD"),
        "SV": ("PR", "AL"),
    }

    @classmethod
    def can_be_created_by(cls, user, target_role=None, **context):
        if not user.is_authenticated:
            return False
        return target_role in cls.MANAGEABLE_ROLES_BY.get(user.role, ())

    def editable_fields_for(self, user):
        if not user.is_authenticated:
            return ()
        if user.is_superuser or user.role == self.Role.SUPERADMIN:
            return self.ALL_EDITABLE_FIELDS
        if user.role == self.Role.SUPERVISOR:
            if self.role in (self.Role.PROFESSOR, self.Role.ALUNO):
                return self.ALL_EDITABLE_FIELDS
            return ()
        if user.role == self.Role.PACIENTE and self.pk == user.pk:
            return self.ADDRESS_FIELDS
        return ()

    def can_be_deleted_by(self, user):
        if not user.is_authenticated:
            return False
        return self.role in self.MANAGEABLE_ROLES_BY.get(user.role, ())


    def clean(self):
        super().clean()
        if self.role == self.Role.ALUNO and not self.matricula:
            raise ValidationError({"matricula":"Aluno precisa de matricula."})

        if self.role in(self.Role.PROFESSOR,self.Role.SUPERVISOR) and not self.crp:
            raise ValidationError({"crp":"Professor/Supervisor precisa ter o crp"})
    
    def __str__(self):
        return f"{self.nome_completo} / {self.email}"
        
    
    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = 'Usuários'
