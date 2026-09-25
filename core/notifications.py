from audit.models import SecurityLog


def enviar_credenciais_por_telefone(user, senha_temporaria, usuario_responsavel=None):
    SecurityLog.objects.create(
        user=usuario_responsavel or user,
        action=SecurityLog.Action.CREATE,
        detail=f"Envio de credenciais por telefone (simulado, sem SMS real) para {user.telefone}.",
        target_model=f"{user._meta.app_label}.{type(user).__name__}",
        target_id=str(user.pk),
    )
    return True