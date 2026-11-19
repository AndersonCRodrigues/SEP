# Create your models here.
from django.db import models
import uuid
from django.conf import settings
from core.permissions import BusinessRulesMixin,ALL,RoleScopedQuerySet
from core.models import CustomUser

Role=CustomUser.Role



def register():
    return{
        "nome":{},
        "cpf":{},
        "nascimento":{},
        "telefone":{},
        "email":{},
        "logradouro":{},
        "cep":{},
        "number":{},
        "municipality":{},
        "bairro":{},
        "city":{},
        "state":{},
        "complement":{},
        "acompanhante":{},
        "responsavel":{},
        "parentesco":{},
    }
class Cookie_draftQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {Role.ADMINISTRATIVO: ALL}
class Cookie_draft(BusinessRulesMixin, models.Model):
    objects = Cookie_draftQuerySet.as_manager()
    STATUS_CHOICE = [
        ('pending','Pendente'),
        ('current','atual'),
        ('done','finalizada'),
    ]
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    answered_by =models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='draft'
    )
    status=models.CharField(
        max_length=20,
        choices=STATUS_CHOICE,
        default="pending"
    )
    data=models.JSONField(default=register)
    create=models.DateTimeField(auto_now_add=True)
    realese=models.DateTimeField(auto_now=True)
    
    
    CREATABLE_BY = (Role.ADMINISTRATIVO,)
    EDITABLE_FIELDS = {Role.ADMINISTRATIVO:("data")}
    DELETABLE_BY=()
    