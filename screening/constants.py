"""
Constantes de triagem sem dependencia de models.

Existe para que patient/models.py possa filtrar por situacao da triagem sem
importar screening.models -- o caminho inverso ja existe (screening -> patient)
e criaria ciclo.
"""

from django.db import models


class ScreeningStatus(models.TextChoices):
    OPEN = "AB", "Aberta"
    CLOSED = "FE", "Fechada"
    REFERRED = "EN", "Encaminhada"
