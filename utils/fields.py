from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models

def get_fernet() -> Fernet:
    key = settings.FIELD_ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)

class EncryptedFieldMixin:
    def get_internal_type(self):
        return "TextField"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        token = get_fernet().encrypt(str(value).encode())
        return token.decode()

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        try:
            return get_fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            raise ValueError(
                "Nao foi possivel descriptografar o campo."
            )
        
    def to_python(self, value):
        return value

class EncryptedCharField(EncryptedFieldMixin, models.CharField):
    pass

class EncryptedTextField(EncryptedFieldMixin, models.TextField):
    pass
