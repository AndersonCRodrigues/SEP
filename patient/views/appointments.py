from django.contrib import messages
from django.db import DatabaseError, IntegrityError, transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, TemplateView

from scheduling.models import AppointmentRequest

from ..forms import AppointmentRequestForm
from ..models import Patient
from .access import PatientOnly
from .sessions import attendant_name, relative_day, session_badge, upcoming_appointments

RequestStatus = AppointmentRequest.Status

REQUEST_LEVELS = {
    RequestStatus.PENDING: "warning",
    RequestStatus.ACCEPTED: "success",
    RequestStatus.DECLINED: "danger",
}


class PatientAppointmentsView(PatientOnly, TemplateView):
    template_name = "patient/agendamentos.html"

    COLUMN_LABELS = ("Data e hora:", "Atendimento por:", "Situação:")
    REQUESTS_SHOWN = 5
    UNAVAILABLE = "Não foi possível carregar seus agendamentos agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.localtime()
        context["column_labels"] = self.COLUMN_LABELS

        try:
            context["appointments"] = [
                self.as_row(appointment, now)
                for appointment in upcoming_appointments(user, now.date())
            ]
            context["schedule_requests"] = [
                self.as_request(item)
                for item in AppointmentRequest.objects.visible_to(user).order_by(
                    "-created_at"
                )[: self.REQUESTS_SHOWN]
            ]
        except DatabaseError:
            context.update(
                {
                    "appointments": [],
                    "schedule_requests": [],
                    "appointments_error": self.UNAVAILABLE,
                }
            )

        return context

    @staticmethod
    def as_row(appointment, now):
        moment = timezone.localtime(appointment.scheduled_at)
        label, level = session_badge(appointment, now)
        return {
            "when": moment,
            "when_label": f"{relative_day(moment.date(), now.date())} - {moment:%H:%M}",
            "attendant": attendant_name(appointment),
            "label": label,
            "level": level,
        }

    @staticmethod
    def as_request(item):
        return {
            "preferred_date": item.preferred_date,
            "period": item.get_preferred_period_display(),
            "label": item.get_status_display(),
            "level": REQUEST_LEVELS[item.status],
            "created_at": item.created_at,
            "response": item.response,
        }


class AppointmentRequestView(PatientOnly, FormView):
    template_name = "patient/solicitar_horario.html"
    form_class = AppointmentRequestForm
    success_url = reverse_lazy("patient:agendamentos")

    PENDING = "Você já tem uma solicitação de horário pendente."
    SENT = "Solicitação enviada. Aguarde a resposta do Administrativo."
    UNAVAILABLE = "Não foi possível registrar sua solicitação agora."
    NOT_FOUND = "Seu cadastro de paciente não foi encontrado."

    def test_func(self):
        return super().test_func() and AppointmentRequest.can_be_created_by(
            self.request.user
        )

    def pending_request(self):
        return (
            AppointmentRequest.objects.visible_to(self.request.user)
            .filter(status=RequestStatus.PENDING)
            .first()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context["pending_request"] = self.pending_request()
        except DatabaseError:
            context["request_error"] = self.UNAVAILABLE
        return context

    def post(self, request, *args, **kwargs):
        try:
            pending = self.pending_request()
        except DatabaseError:
            messages.error(request, self.UNAVAILABLE)
            return redirect(self.success_url)

        if pending:
            messages.error(request, self.PENDING)
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        patient = Patient.objects.visible_to(self.request.user).first()
        if patient is None:
            form.add_error(None, self.NOT_FOUND)
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                form.save_for(patient)
        except IntegrityError:
            messages.error(self.request, self.PENDING)
            return redirect(self.success_url)
        except DatabaseError:
            form.add_error(None, self.UNAVAILABLE)
            return self.form_invalid(form)

        messages.success(self.request, self.SENT)
        return super().form_valid(form)
