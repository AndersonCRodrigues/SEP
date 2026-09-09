from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

from .permissions import Role


class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, password=None, **extra_fields):
        if extra_fields.get("role") == Role.PACIENTE:
            if not email and not extra_fields.get("cpf"):
                raise ValueError(_("Paciente precisa de e-mail ou CPF."))
        elif not email:
            raise ValueError(_("Funcionário precisa de e-mail."))
        email = self.normalize_email(email) if email else None
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("Superuser precisa de e-mail."))
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "SA")

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser precisa ter is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser precisa ter is_superuser=True."))

        return self.create_user(email, password, **extra_fields)
