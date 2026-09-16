from datetime import date, datetime, timedelta

from django.utils import timezone

from .models import Appointment, RoomBooking


def running_appointments(user, instant=None):
    instant = instant or timezone.localtime()
    running = {}

    for appointment in Appointment.objects.visible_to(user).filter(
        room__isnull=False,
        scheduled_at__lte=instant,
        scheduled_at__gt=instant - timedelta(days=1),
    ):
        starts = timezone.localtime(appointment.scheduled_at)
        if instant < starts + timedelta(minutes=appointment.duration_minutes):
            running[appointment.room_id] = appointment

    return running


def busy_until(user, instant=None, running=None):
    instant = instant or timezone.localtime()
    if running is None:
        running = running_appointments(user, instant)

    ends = {
        booking.room_id: (
            datetime.combine(date.min, booking.start_time) + RoomBooking.DURATION
        ).time()
        for booking in RoomBooking.objects.visible_to(user)
        .occupying(instant)
        .filter(room__isnull=False)
    }

    for room_id, appointment in running.items():
        finishes = (
            timezone.localtime(appointment.scheduled_at)
            + timedelta(minutes=appointment.duration_minutes)
        ).time()
        ends[room_id] = max(finishes, ends.get(room_id, finishes))

    return ends
