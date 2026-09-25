from django.core.paginator import Paginator
from django.db import DatabaseError
from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from django.views.generic import TemplateView

from scheduling.models import Appointment

from .access import PatientOnly
from .sessions import SESSION_STATUS, Status, attendant_name, relative_day

HISTORY_STATUS = SESSION_STATUS | {
    Status.SCHEDULED: ("Aguardando registro", "secondary"),
}

HISTORY_MESSAGES = {
    Status.ATTENDED: "Sessão realizada.",
    Status.PATIENT_NO_SHOW: "Sua falta foi registrada nesta sessão.",
    Status.STUDENT_NO_SHOW: "A sessão não aconteceu por ausência de quem atenderia.",
    Status.CANCELLED: "Esta sessão foi cancelada.",
    Status.SCHEDULED: "O registro desta sessão ainda não foi feito pela equipe.",
}


def history_appointments(user, today):
    return (
        Appointment.objects.visible_to(user)
        .filter(~Q(status=Status.SCHEDULED) | Q(scheduled_at__date__lt=today))
        .select_related("assigned_student", "teacher")
        .order_by("-scheduled_at")
    )


class PatientHistoryView(PatientOnly, TemplateView):
    template_name = "patient/historico.html"

    COLUMN_LABELS = ("Data e hora:", "Atendimento por:", "Situação:")
    PER_PAGE = 10
    UNAVAILABLE = "Não foi possível carregar seu histórico agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["column_labels"] = self.COLUMN_LABELS
        today = timezone.localdate()

        try:
            page = Paginator(
                history_appointments(self.request.user, today), self.PER_PAGE
            ).get_page(self.request.GET.get("pagina"))
            context.update(
                {
                    "page": page,
                    "sessions": [
                        self.as_row(appointment, today) for appointment in page
                    ],
                }
            )
        except DatabaseError:
            context.update({"sessions": [], "history_error": self.UNAVAILABLE})

        return context

    @staticmethod
    def as_row(appointment, today):
        moment = timezone.localtime(appointment.scheduled_at)
        label, level = HISTORY_STATUS[appointment.status]
        return {
            "pk": appointment.pk,
            "when": moment,
            "when_label": f"{relative_day(moment.date(), today)} - {moment:%H:%M}",
            "attendant": attendant_name(appointment),
            "label": label,
            "level": level,
        }


class PatientSessionDetailView(PatientOnly, TemplateView):
    template_name = "patient/historico_detalhe.html"

    UNAVAILABLE = "Não foi possível carregar esta sessão agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            appointment = (
                history_appointments(self.request.user, timezone.localdate())
                .filter(pk=self.kwargs["pk"])
                .first()
            )
        except DatabaseError:
            return context | {"session_error": self.UNAVAILABLE}

        if appointment is None:
            raise Http404("Sessão não encontrada.")

        context["session"] = self.as_detail(appointment)
        return context

    @staticmethod
    def as_detail(appointment):
        label, level = HISTORY_STATUS[appointment.status]
        return {
            "when": timezone.localtime(appointment.scheduled_at),
            "kind": appointment.get_kind_display(),
            "duration": appointment.duration_minutes,
            "attendant": attendant_name(appointment),
            "teacher": (
                appointment.teacher.get_full_name() if appointment.teacher else ""
            ),
            "label": label,
            "level": level,
            "message": HISTORY_MESSAGES[appointment.status],
        }
