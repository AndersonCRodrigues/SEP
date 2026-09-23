from django.db import DatabaseError
from django.views.generic import TemplateView
from scheduling.models import Room
from scheduling.occupancy import busy_until, running_appointments
from .access import AdministrativeOnly


class RoomsView(AdministrativeOnly, TemplateView):
    template_name = "administration/salas.html"

    UNAVAILABLE = "Não foi possível consultar as salas agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        try:
            rooms = list(Room.objects.visible_to(user))
            running = running_appointments(user)
            busy = busy_until(user, running=running)
        except DatabaseError:
            return context | {"rooms": [], "rooms_error": self.UNAVAILABLE}

        context["rooms"] = [self.as_card(room, busy, running) for room in rooms]
        return context

    @staticmethod
    def as_card(room, busy, running):
        if room.status == Room.Status.MAINTENANCE:
            state, label, level = "maintenance", room.get_status_display(), "warning"
        elif room.status == Room.Status.INACTIVE:
            state, label, level = "inactive", room.get_status_display(), "secondary"
        elif room.pk in busy:
            state = "occupied"
            label = f"Ocupada até {busy[room.pk]:%H:%M}"
            level = "danger"
        else:
            state, label, level = "available", "Disponível", "success"

        return {
            "room": room,
            "state": state,
            "label": label,
            "level": level,
            "activity": (
                running[room.pk].get_kind_display() if room.pk in running else None
            ),
        }
