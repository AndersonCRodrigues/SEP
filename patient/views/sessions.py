from scheduling.models import Appointment

Status = Appointment.Status
Presence = Appointment.PresenceStatus

SESSION_STATUS = {
    Status.ATTENDED: ("Concluída", "success"),
    Status.PATIENT_NO_SHOW: ("Faltou", "danger"),
    Status.STUDENT_NO_SHOW: ("Não realizada", "warning"),
    Status.CANCELLED: ("Cancelada", "secondary"),
}

PRESENCE_LEVELS = {
    Presence.CONFIRMED: "success",
    Presence.AWAITING: "warning",
    Presence.SCHEDULED: "secondary",
}


def relative_day(day, today):
    difference = (day - today).days
    if difference == 0:
        return "Hoje"
    if difference == 1:
        return "Amanhã"
    if difference == -1:
        return "Ontem"
    return f"{day:%d/%m/%Y}"


def attendant_name(appointment):
    attendant = appointment.assigned_student or appointment.teacher
    return attendant.get_full_name() if attendant else ""


def session_badge(appointment, now):
    presence = appointment.presence_status(now)
    if presence:
        return presence.label, PRESENCE_LEVELS[presence]
    return SESSION_STATUS[appointment.status]


def upcoming_appointments(user, today):
    return (
        Appointment.objects.visible_to(user)
        .filter(status=Status.SCHEDULED, scheduled_at__date__gte=today)
        .select_related("assigned_student", "teacher")
        .order_by("scheduled_at")
    )
