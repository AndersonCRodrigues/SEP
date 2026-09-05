from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from .fields import only_digits

UserModel = get_user_model()


class EmailOUMatricula(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            return None

        identificador = Q(email__iexact=username) | Q(matricula__iexact=username)

        digitos = only_digits(username)
        if digitos:
            identificador |= Q(cpf=digitos)

        try:
            user = UserModel.objects.get(identificador)
        except UserModel.DoesNotExist:
            return None

        except UserModel.MultipleObjectsReturned:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
