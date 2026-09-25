from datetime import datetime, time

from django.utils import timezone
from django.views.generic import TemplateView

from core.month_calendar import displayed_month, month_calendar, month_range
from documents.models import AttendanceCertificate, InternshipDeclaration
from scheduling.models import Appointment, Room, RoomBooking
from scheduling.occupancy import busy_until

from .access import AdministrativeOnly


class AdministrativeHomeView(AdministrativeOnly, TemplateView):
    template_name = "administration/home_administration.html"

    ACTIVITIES_SHOWN = 5

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()

        context.update(self.operational_summary(user, today))
        context["recent_activities"] = self.recent_activities(user)
        context.update(self.calendar_context(user, today))
        return context

    def operational_summary(self, user, today):
        return {
            "occupied_rooms": len(busy_until(user)),
            "total_rooms": Room.objects.visible_to(user).usable().count(),
            "appointments_today": (
                Appointment.objects.visible_to(user)
                .filter(scheduled_at__date=today)
                .count()
            ),
            "pending_declarations": (
                AttendanceCertificate.objects.visible_to(user)
                .filter(
                    kind=AttendanceCertificate.Kind.DECLARATION,
                    status=AttendanceCertificate.Status.PENDING,
                )
                .count()
                + InternshipDeclaration.objects.visible_to(user)
                .filter(status=InternshipDeclaration.Status.PENDING)
                .count()
            ),
            "certificates_issued": (
                AttendanceCertificate.objects.visible_to(user)
                .filter(issued_at=today)
                .count()
            ),
        }

    def recent_activities(self, user):
        items = []

        for appointment in (
            Appointment.objects.visible_to(user)
            .select_related("room")
            .order_by("-created_at")[: self.ACTIVITIES_SHOWN]
        ):
            when = timezone.localtime(appointment.scheduled_at)
            items.append(
                {
                    "kind": "appointment",
                    "title": f"{appointment.get_kind_display()} agendada",
                    "detail": (
                        f"{appointment.room or 'Sem sala'} — {when:%d/%m às %H:%M}"
                    ),
                    "when": appointment.created_at,
                }
            )

        for document in (
            AttendanceCertificate.objects.visible_to(user)
            .select_related("patient", "student")
            .order_by("-issued_at", "-created_at")[: self.ACTIVITIES_SHOWN]
        ):
            items.append(
                {
                    "kind": "document",
                    "title": f"{document.get_kind_display()} emitido",
                    "detail": str(document.person),
                    "when": document.created_at,
                }
            )

        for booking in (
            RoomBooking.objects.visible_to(user)
            .select_related("room")
            .filter(end_date__isnull=False)
            .order_by("-end_date")[: self.ACTIVITIES_SHOWN]
        ):
            items.append(
                {
                    "kind": "room",
                    "title": "Sala liberada",
                    "detail": f"{booking.room or 'Sala removida'} — "
                    f"{booking.get_weekday_display()} {booking.start_time:%H:%M}",
                    "when": self.as_instant(booking.end_date),
                }
            )

        items.sort(key=lambda item: item["when"], reverse=True)
        return items[: self.ACTIVITIES_SHOWN]

    @staticmethod
    def as_instant(day):
        return timezone.make_aware(datetime.combine(day, time.min))

    def calendar_context(self, user, today):
        year, month = displayed_month(self.request.GET, today)
        first, last = month_range(year, month)

        with_event = set(
            Appointment.objects.visible_to(user)
            .filter(scheduled_at__date__range=(first, last))
            .dates("scheduled_at", "day")
        )

        return month_calendar(year, month, today, with_event)
