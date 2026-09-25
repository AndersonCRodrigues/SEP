from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, View

from documents.models import AttendanceCertificate

from ..forms import MedicalCertificateForm
from .access import CanIssueCertificates


class CertificatesView(CanIssueCertificates, FormView):
    template_name = "administration/atestados.html"
    form_class = MedicalCertificateForm
    success_url = reverse_lazy("administration:atestados")

    RECENT_SHOWN = 5

    def get_form_kwargs(self):
        return super().get_form_kwargs() | {"user": self.request.user}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["appointments_url"] = reverse("administration:atestados_atendimentos")
        context["recent"] = [
            {"name": str(document.person), "issued_at": document.issued_at}
            for document in AttendanceCertificate.objects.visible_to(self.request.user)
            .filter(
                kind=AttendanceCertificate.Kind.MEDICAL_CERTIFICATE,
                status=AttendanceCertificate.Status.ISSUED,
            )
            .select_related("patient", "student")
            .order_by("-issued_at", "-created_at")[: self.RECENT_SHOWN]
        ]
        return context

    def form_valid(self, form):
        certificate = form.issue(self.request.user)
        messages.success(self.request, f"Atestado de {certificate.person} emitido.")
        return super().form_valid(form)


class CertificateAppointmentsView(CanIssueCertificates, View):
    def get(self, request):
        field = MedicalCertificateForm.base_fields["appointment"]
        appointments = MedicalCertificateForm.appointments_for(
            request.GET.get("person"), request.user
        )
        return JsonResponse(
            {
                "appointments": [
                    {
                        "id": appointment.pk,
                        "label": field.label_from_instance(appointment),
                    }
                    for appointment in appointments
                ]
            }
        )
