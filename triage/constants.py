from django.db import models


class TriageStatus(models.TextChoices):
    OPEN = "AB", "Aberta"
    CLOSED = "FE", "Fechada"
    REFERRED = "EN", "Encaminhada"
