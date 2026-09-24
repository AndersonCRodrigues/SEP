from datetime import timedelta

EDIT_MARGIN = timedelta(minutes=1)
NEW_FEEDBACK_HOURS = 24


def referral_status(case, today):
    # TODO: dado mockado. O CaseAssignment não guarda quem encaminhou nem a
    # confirmação; trocar quando o encaminhamento ganhar esses campos.
    if case.start_date == today:
        return {
            "situation": "Aguardando confirmação",
            "label": "Pendente",
            "level": "danger",
        }
    return {
        "situation": "Encaminhado por Supervisor geral",
        "label": "Ativo",
        "level": "success",
    }


def feedback_status(created_at, updated_at, now):
    # TODO: dado mockado. Não existe marcação de leitura por aluno; trocar
    # quando o feedback registrar quem leu e quando.
    if updated_at - created_at > EDIT_MARGIN:
        return "Editada", "danger"
    if created_at >= now - timedelta(hours=NEW_FEEDBACK_HOURS):
        return "Novo", "warning"
    return "Lida", "success"


def record_status(note):
    # TODO: dado mockado. O produto ainda não definiu o critério de "Revisar"
    # contra "Pendente"; por ora segue a confirmação do supervisor.
    if note.pending_confirmation:
        return "Pendente", "danger"
    return "Revisar", "success"
