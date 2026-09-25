from django.db import DatabaseError
from django.db.models import Q, Value
from django.db.models.functions import Replace
from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.views.generic import DetailView, TemplateView, View
from core.fields import only_digits
from patient.models import Patient
from utils.masking import mask_cpf
from ..patient_registration import STEPS, PatientRegistration
from .access import AdministrativeOnly, CanRegisterPatients

COLUMNS = ("Nome:", "CPF:", "Situação:", "Cadastrado em:")

FlowStatus = Patient.FlowStatus
NO_FLOW = ("Sem fluxo definido", "secondary")

FLOW_LEVELS = {
    FlowStatus.AWAITING_TRIAGE: "warning",
    FlowStatus.IN_TRIAGE: "warning",
    FlowStatus.AWAITING_REVIEW: "warning",
    FlowStatus.REFERRED: "success",
    FlowStatus.IN_TREATMENT: "success",
    FlowStatus.DISCHARGED: "secondary",
}


def situation(patient):
    if not patient.flow_status:
        return NO_FLOW
    return patient.get_flow_status_display(), FLOW_LEVELS[patient.flow_status]


class PatientsView(AdministrativeOnly, TemplateView):
    template_name = "administration/pacientes.html"

    UNAVAILABLE = "Não foi possível carregar os pacientes agora."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["columns"] = COLUMNS
        context["situations"] = FlowStatus.choices
        context["search"] = self.request.GET.get("q", "").strip()
        context["situation_filter"] = self.request.GET.get("situacao", "")

        try:
            context["patients"] = [
                self.as_row(paciente) for paciente in self.listed(self.request.user)
            ]
        except DatabaseError:
            context.update({"patients": [], "patients_error": self.UNAVAILABLE})

        return context

    @staticmethod
    def as_row(paciente):
        label, level = situation(paciente)
        return {
            "patient": paciente,
            "name": paciente.get_full_name(),
            "cpf": mask_cpf(paciente.cpf),
            "label": label,
            "level": level,
            "registered_at": paciente.created_at,
        }

    def listed(self, user):
        pacientes = Patient.objects.visible_to(user).order_by("first_name", "last_name")

        busca = self.request.GET.get("q", "").strip()
        if busca:
            pacientes = self.matching(pacientes, busca)

        situacao = self.request.GET.get("situacao", "")
        if situacao in FlowStatus.values:
            pacientes = pacientes.filter(flow_status=situacao)

        return pacientes

    @staticmethod
    def matching(pacientes, busca):
        """O CPF é gravado com e sem pontuação, então a busca compara dígitos."""
        procura = Q(first_name__icontains=busca) | Q(last_name__icontains=busca)

        digitos = only_digits(busca)
        if digitos:
            apenas_digitos = Replace(
                Replace(Replace("cpf", Value("."), Value("")), Value("-"), Value("")),
                Value(" "),
                Value(""),
            )
            pacientes = pacientes.annotate(cpf_digitos=apenas_digitos)
            procura |= Q(cpf_digitos__contains=digitos)

        return pacientes.filter(procura)


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
