from django.db import models

# Mora no core, e nao no app triage, porque o patient precisa dele para montar
# o recorte do aluno e o triage importa o patient de volta. Enum puro, sem
# tabela: e o mesmo caso do Role.


class TriageStatus(models.TextChoices):
    OPEN = "AB", "Aberta"
    SUBMITTED = "EV", "Enviada"
    CLOSED = "FE", "Fechada"
    REFERRED = "EN", "Encaminhada"


# Enquanto o supervisor nao decide, a ficha ainda e do aluno que a escreveu:
# ele le, mas so edita enquanto aberta.
VISIBLE_TO_AUTHOR = (TriageStatus.OPEN, TriageStatus.SUBMITTED)
