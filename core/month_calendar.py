from calendar import Calendar, monthrange
from datetime import date, timedelta

MONTH_NAMES = [
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
]


def displayed_month(params, today):
    try:
        year = int(params.get("ano", today.year))
        month = int(params.get("mes", today.month))
        date(year, month, 1)
    except (TypeError, ValueError):
        return today.year, today.month
    return year, month


def month_range(year, month):
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def month_calendar(year, month, today, event_days):
    first, last = month_range(year, month)
    weeks = [
        [
            {
                "date": day,
                "in_month": day.month == month,
                "today": day == today,
                "has_event": day in event_days,
            }
            for day in week
        ]
        for week in Calendar(firstweekday=6).monthdatescalendar(year, month)
    ]

    return {
        "calendar_year": year,
        "calendar_month": month,
        "calendar_weeks": weeks,
        "calendar_months": list(enumerate(MONTH_NAMES, start=1)),
        "calendar_years": range(today.year - 2, today.year + 3),
        "previous_month": first - timedelta(days=1),
        "next_month": last + timedelta(days=1),
    }
