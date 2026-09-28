from datetime import timedelta

ANALYSIS_DEADLINE_HOURS = 24


def submitted_at(record):
    # TODO: dado mockado. A ficha não guarda quando o aluno enviou; por ora
    # vale a data de criação. Trocar quando o envio for registrado.
    return record.created_at


def triage_status(record, now):
    # TODO: dado mockado. Não existe prazo de análise nem data de alteração da
    # ficha; "Atrasada" usa 24 horas desde o envio e "Editada" marca a ficha já
    # analisada. Trocar quando prazo e edição existirem.
    if record.closed_at is not None:
        return "Editada", "success"
    if submitted_at(record) < now - timedelta(hours=ANALYSIS_DEADLINE_HOURS):
        return "Atrasada", "danger"
    return "Analisar", "warning"
