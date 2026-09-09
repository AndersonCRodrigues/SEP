from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from localflavor.br.models import BRStateField, BRPostalCodeField
from .fields import DigitsBRCPFField, only_digits
from .managers import CustomUserManager
from .permissions import Role as UserRole


class CustomUser(AbstractUser):
    Role = UserRole

    username = None
    email = models.EmailField(_("Adicionar email"), unique=True, null=True, blank=True)

    nome_completo = models.CharField(max_length=350, verbose_name="Nome Completo")
    cpf = DigitsBRCPFField(unique=True, verbose_name="CPF")
    telefone = models.CharField(max_length=20, verbose_name="Telefone")
    data_nascimento = models.DateField(
        null=True, blank=True, verbose_name="Data de nascimento"
    )

    logradouro = models.CharField(max_length=200, verbose_name="Logradouro")
    numero = models.CharField(max_length=10, verbose_name="Número")
    complemento = models.CharField(
        max_length=100, blank=True, verbose_name="Complemento"
    )
    bairro = models.CharField(max_length=100, verbose_name="Bairro")
    cidade = models.CharField(max_length=100, verbose_name="Cidade")
    estado = BRStateField(verbose_name="Estado")
    cep = BRPostalCodeField(verbose_name="CEP")
    must_change_password = models.BooleanField(default=False,verbose_name="Precisa trocar a senha",)

    role = models.CharField(
        max_length=2, choices=Role.choices, default=Role.ALUNO, verbose_name="Cargo"
    )

    matricula = models.CharField(
        max_length=20, unique=True, null=True, blank=True, verbose_name="Matricula"
    )
    crp = models.CharField(max_length=15, blank=True, verbose_name="CRP")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo", "cpf"]

    objects = CustomUserManager()

    ADDRESS_FIELDS = (
        "telefone",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cidade",
        "estado",
        "cep",
    )
    ALL_EDITABLE_FIELDS = (
        "nome_completo",
        "email",
        "cpf",
        "data_nascimento",
        "role",
        "matricula",
        "crp",
    ) + ADDRESS_FIELDS

    def enforce_role(self):
        """Subclasse de heranca multi-tabela fixa o proprio papel."""

    def clean(self):
        self.enforce_role()
        super().clean()
        if not self.email:
            self.email = None
        if not self.matricula:
            self.matricula = None

        if self.role != self.Role.PACIENTE and not self.email:
            raise ValidationError(
                {"email": "Funcionário precisa de e-mail para acessar o sistema."}
            )

        if (
            self.role in (self.Role.ALUNO, self.Role.ADMINISTRATIVO)
            and not self.matricula
        ):
            raise ValidationError(
                {"matricula": "Aluno e Administrativo precisam de matrícula."}
            )

        if self.role in (self.Role.PROFESSOR, self.Role.SUPERVISOR) and not self.crp:
            raise ValidationError({"crp": "Professor/Supervisor precisa ter o CRP."})

    def save(self, *args, **kwargs):
        self.enforce_role()
        if not self.email:
            self.email = None
        if not self.matricula:
            self.matricula = None
        self.cpf = only_digits(self.cpf)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome_completo} / {self.email or self.cpf}"

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
