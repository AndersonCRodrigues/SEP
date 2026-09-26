from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from localflavor.br.models import BRPostalCodeField, BRStateField

from .fields import (
    DigitsBRCPFField,
    collapse_spaces,
    format_cep,
    normalize_address_number,
    normalize_phone,
    only_digits,
)
from .managers import CustomUserManager
from .permissions import Role as UserRole
from .validators import validate_address_number, validate_letters, validate_phone


class CustomUser(AbstractUser):
    Role = UserRole

    username = None
    email = models.EmailField(_("Adicionar email"), unique=True, null=True, blank=True)

    first_name = models.CharField(
        max_length=150, validators=[validate_letters], verbose_name="Nome"
    )
    last_name = models.CharField(
        max_length=150, validators=[validate_letters], verbose_name="Sobrenome"
    )
    cpf = DigitsBRCPFField(unique=True, verbose_name="CPF")
    telefone = models.CharField(
        max_length=20, validators=[validate_phone], verbose_name="Telefone"
    )
    data_nascimento = models.DateField(
        null=True, blank=True, verbose_name="Data de nascimento"
    )

    logradouro = models.CharField(max_length=200, verbose_name="Logradouro")
    numero = models.CharField(
        max_length=10, validators=[validate_address_number], verbose_name="Número"
    )
    complemento = models.CharField(
        max_length=100, blank=True, verbose_name="Complemento"
    )
    bairro = models.CharField(max_length=100, verbose_name="Bairro")
    cidade = models.CharField(
        max_length=100, validators=[validate_letters], verbose_name="Cidade"
    )
    estado = BRStateField(verbose_name="Estado")
    cep = BRPostalCodeField(verbose_name="CEP")
    must_change_password = models.BooleanField(
        default=False,
        verbose_name="Precisa trocar a senha",
    )

    role = models.CharField(
        max_length=2, choices=Role.choices, default=Role.ALUNO, verbose_name="Cargo"
    )

    matricula = models.CharField(
        max_length=20, unique=True, null=True, blank=True, verbose_name="Matricula"
    )
    crp = models.CharField(max_length=15, blank=True, verbose_name="CRP")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "cpf"]

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
        "first_name",
        "last_name",
        "email",
        "cpf",
        "data_nascimento",
        "role",
        "matricula",
        "crp",
    ) + ADDRESS_FIELDS

    def enforce_role(self):
        """Subclasse de heranca multi-tabela fixa o proprio papel."""

    def normalize(self):
        self.enforce_role()
        self.email = self.email or None
        self.matricula = self.matricula or None
        self.cpf = only_digits(self.cpf)
        self.telefone = normalize_phone(self.telefone)
        self.cep = format_cep(self.cep)
        self.numero = normalize_address_number(self.numero)
        self.first_name = collapse_spaces(self.first_name)
        self.last_name = collapse_spaces(self.last_name)
        self.cidade = collapse_spaces(self.cidade)

    def clean_fields(self, exclude=None):
        self.normalize()
        super().clean_fields(exclude=exclude)

    def clean(self):
        self.normalize()
        super().clean()
        self.email = self.email or None

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
            raise ValidationError({"crp": "Professor/Coordenador precisa ter o CRP."})

    def save(self, *args, **kwargs):
        self.normalize()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name()} / {self.email or self.cpf}"

    @property
    def nome_completo(self):
        return self.get_full_name()

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
