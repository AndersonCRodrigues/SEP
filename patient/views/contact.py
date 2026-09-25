from urllib.parse import quote

from django.conf import settings
from django.db import DatabaseError
from django.views.generic import TemplateView

from core.fields import only_digits

from ..models import Patient
from .access import PatientOnly


def initials(person):
    return "".join(
        name.strip()[0].upper()
        for name in (person.first_name, person.last_name)
        if name and name.strip()
    )


class PatientContactView(PatientOnly, TemplateView):
    template_name = "patient/contato.html"

    UNAVAILABLE = "Não foi possível carregar quem cuida do seu atendimento agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = settings.SEP_CONTACT
        context.update(
            {
                "service_name": contact.get("name") or "Serviço Escola de Psicologia",
                "channels": self.channels(contact),
            }
        )

        try:
            context["caregivers"] = self.caregivers(self.request.user)
        except DatabaseError:
            context.update({"caregivers": [], "caregivers_error": self.UNAVAILABLE})

        return context

    @staticmethod
    def caregivers(user):
        patient = Patient.objects.visible_to(user).first()
        if patient is None:
            return []
        return [
            {"name": case.student.get_full_name(), "initials": initials(case.student)}
            for case in patient.assignment_history.filter(end_date__isnull=True)
            .select_related("student")
            .order_by("start_date", "pk")
        ]

    @staticmethod
    def channels(contact):
        channels = []
        city = (contact.get("city") or "").strip()
        phone = (contact.get("phone") or "").strip()
        email = (contact.get("email") or "").strip()

        if city:
            place = ", ".join(filter(None, [contact.get("name"), city]))
            channels.append(
                {
                    "kind": "location",
                    "label": "Localização",
                    "value": city,
                    "href": "https://www.google.com/maps/search/?api=1&query="
                    + quote(place),
                    "external": True,
                }
            )
        if only_digits(phone):
            channels.append(
                {
                    "kind": "phone",
                    "label": "Telefone",
                    "value": phone,
                    "href": f"tel:+55{only_digits(phone)}",
                }
            )
        if email:
            channels.append(
                {
                    "kind": "email",
                    "label": "E-mail",
                    "value": email,
                    "href": f"mailto:{email}",
                }
            )
        return channels
