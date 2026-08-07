from django.db import models
from core.models import CustomUser
from areas.models import AreaActing

class Professor(CustomUser):

    area_atuacao = models.ForeignKey(
        AreaActing,
        on_delete=models.PROTECT,
        related_name="professores"
    )