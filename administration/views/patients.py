from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.views.generic import DetailView, TemplateView, View
from patient.models import Patient
from ..patient_registration import STEPS, PatientRegistration
from .access import AdministrativeOnly, CanRegisterPatients


class PatientsView(AdministrativeOnly, TemplateView):
    template_name = "administration/pacientes.html"


def to_step(step):
    return redirect("administration:cadastrar_paciente_etapa", step=step.slug)


class PatientRegistrationStartView(CanRegisterPatients, View):
    def get(self, request):
        PatientRegistration.start(request.session)
        return to_step(STEPS[0])


class PatientRegistrationStepView(CanRegisterPatients, View):
    template_name = "administration/cadastrar_paciente.html"

    def get(self, request, step):
        wizard = PatientRegistration(request.session)
        current = wizard.step(step)
        if current is None:
            return to_step(STEPS[0])
        if wizard.is_ahead(current):
            return to_step(wizard.first_unanswered())

        form = current.form_class(initial=wizard.answer(current))
        return self.respond(request, wizard, current, form)

    def post(self, request, step):
        wizard = PatientRegistration(request.session)
        current = wizard.step(step)
        if current is None:
            return to_step(STEPS[0])

        if request.POST.get("action") == "back":
            previous, _ = wizard.neighbours(current)
            wizard.save(current, request.POST)
            return to_step(previous or current)

        form = current.form_class(data=request.POST)
        if not form.is_valid():
            return self.respond(request, wizard, current, form)

        wizard.save(current, request.POST)
        _, following = wizard.neighbours(current)
        if following:
            return to_step(following)

        pending = wizard.first_unanswered()
        if pending:
            return to_step(pending)

        try:
            patient = wizard.complete(request.user)
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
            return to_step(STEPS[0])

        return redirect("administration:cadastro_concluido", pk=patient.pk)

    def respond(self, request, wizard, step, form):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "step": step,
                "number": wizard.number(step),
                "total": len(STEPS),
                "is_first": step == STEPS[0],
                "sections": wizard.sections(step),
            },
        )


class RegistrationCompletedView(CanRegisterPatients, DetailView):
    template_name = "administration/cadastro_concluido.html"
    context_object_name = "patient"

    def get_queryset(self):
        return Patient.objects.visible_to(self.request.user).select_related(
            "registered_by"
        )
