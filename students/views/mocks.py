from datetime import timedelta

from django.utils import timezone

EDIT_MARGIN = timedelta(minutes=1)
NEW_FEEDBACK_HOURS = 24

PENDING_TRIAGES = (
    ("José Santos", "Prof.º Jorge Junior", 0, 11),
    ("Camila Duarte", "Prof.ª Renata Alves", 1, 9),
    ("Rafael Nunes", "Coordenação geral", 2, 14),
    ("Ana Beatriz", "Prof. Marcos Lima", 3, 16),
    ("Lucas Prado", "Prof.º Jorge Junior", 6, 10),
)


def pending_triages(student):
    # TODO: dado mockado. Trocar pela triagem designada ao aluno, com quem
    # encaminhou e a data do encaminhamento, quando esse vínculo existir.
    today = timezone.localtime()
    return [
        {
            "patient": patient,
            "referred_by": referred_by,
            "referred_at": (today - timedelta(days=days)).replace(
                hour=hour, minute=39, second=0, microsecond=0
            ),
        }
        for patient, referred_by, days, hour in PENDING_TRIAGES
    ]


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
        "situation": "Encaminhado por Coordenação geral",
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
