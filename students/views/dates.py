from django.utils import timezone


def updated_label(moment, now):
    if moment is None:
        return "Sem evolução registrada"

    moment = timezone.localtime(moment)
    days = (now.date() - moment.date()).days

    if days >= 1:
        return f"Atualizado há {days} dia" + ("s" if days > 1 else "")

    hours = int((now - moment).total_seconds() // 3600)
    if hours >= 1:
        return f"Atualizado há {hours}h"

    return "Atualizado hoje"


def received_label(moment, now):
    moment = timezone.localtime(moment)
    days = (now.date() - moment.date()).days

    if days == 0:
        return f"Recebida às {moment:%H:%M}"
    if days == 1:
        return "Recebida ontem"

    return f"Recebida em {moment:%d/%m/%Y}"
