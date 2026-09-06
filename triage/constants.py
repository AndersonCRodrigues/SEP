from django.db import models


class TriageStatus(models.TextChoices):
    OPEN = "AB", "Aberta"
    SUBMITTED = "EV", "Enviada"
    CLOSED = "FE", "Fechada"
    REFERRED = "EN", "Encaminhada"


VISIBLE_TO_AUTHOR = (TriageStatus.OPEN, TriageStatus.SUBMITTED)
