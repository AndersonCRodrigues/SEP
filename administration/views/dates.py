from calendar import monthrange
from datetime import timedelta

WEEKDAY_NAMES = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]


def day_label(day, today):
    difference = (day - today).days
    if difference == 0:
        return "Hoje"
    if difference == -1:
        return "Ontem"
    if difference == 1:
        return "Amanhã"
    if abs(difference) < 7:
        return WEEKDAY_NAMES[day.weekday()]
    return f"{day:%d/%m/%Y}"


def period_range(period, today):
    if period == "hoje":
        return today, today
    if period == "semana":
        first = today - timedelta(days=(today.weekday() + 1) % 7)
        return first, first + timedelta(days=6)
    if period == "mes":
        last_day = monthrange(today.year, today.month)[1]
        return today.replace(day=1), today.replace(day=last_day)
    return None
