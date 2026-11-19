from dataclasses import dataclass
from django.core.exceptions import ValidationError
from django.db import transaction

from core.utils import sincronizar_grupo
from patient.models import Patient

from . import forms

SESSION_KEY = "patient_registration"
SESSION_KEY_COMPLETED = "patient_registration_completed"

SECTIONS = ("Identificação", "Contatos", "Endereço", "Acompanhante", "Encerramento")


@dataclass(frozen=True)
class Step:
    slug: str
    section: str
    title: str
    icon: str
    form_class: type
    only_if_accompanied: bool = False


STEPS = (
    Step("nome", "Identificação", "Nome completo", "person", forms.FullNameForm),
    Step("cpf", "Identificação", "CPF", "person", forms.CpfForm),
    Step(
        "nascimento",
        "Identificação",
        "Data de nascimento",
        "calendar",
        forms.BirthDateForm,
    ),
    Step("telefone", "Contatos", "Telefone de contato", "phone", forms.PhoneForm),
    Step("email", "Contatos", "E-mail de contato", "phone", forms.EmailForm),
    
    Step("logradouro", "Endereço", "Endereço completo", "address", forms.LogradouroForm),
    Step("cep", "Endereço", "CEP", "address", forms.CEPForm),
    Step("number", "Endereço", "Número", "address", forms.NumberForm),
    Step("municipality", "Endereço", "Município", "address", forms.MunicipalityForm),
    Step("bairro", "Endereço", "Bairro", "address", forms.BairroForm),
    Step("city", "Endereço", "Cidade", "address", forms.CityForm),
    Step("state", "Endereço", "Estado", "address", forms.StateForm),
    Step("complement", "Endereço", "Complemento", "address", forms.ComplementForm),
    
    
    
    
    Step(
        "acompanhante",
        "Acompanhante",
        "O paciente está acompanhado?",
        "companion",
        forms.AccompaniedForm,
    ),
    Step(
        "responsavel",
        "Acompanhante",
        "Nome do responsável",
        "companion",
        forms.GuardianNameForm,
        only_if_accompanied=True,
    ),
    Step(
        "parentesco",
        "Acompanhante",
        "Grau de parentesco",
        "companion",
        forms.GuardianRelationshipForm,
        only_if_accompanied=True,
    ),
)


class PatientRegistration:
    def __init__(self, draft):
        self.draft=draft
        if self.draft.data is None:
            self.draft.data={}
        self.answers=self.draft.data



    @property
    def accompanied(self):
        return self.answers.get("acompanhante", {}).get("is_accompanied") == "sim"
    @property
    def completed(self):
            return self.draft.status=='done'
        
            

    def steps(self):
        return [
            step for step in STEPS if self.accompanied or not step.only_if_accompanied
        ]

    def step(self, slug):
        return next((step for step in self.steps() if step.slug == slug), None)

    def neighbours(self, step):
        steps = self.steps()
        index = steps.index(step)
        previous = steps[index - 1] if index else None
        following = steps[index + 1] if index + 1 < len(steps) else None
        return previous, following

    def answer(self, step):
        return self.answers.get(step.slug, {})

    def save(self, step, data):
        self.answers[step.slug] = {
            name: data.get(name, "") for name in step.form_class.base_fields
        }
        if not self.accompanied:
            for skipped in STEPS:
                if skipped.only_if_accompanied:
                    self.answers.pop(skipped.slug, None)
        self.draft.save(update_fields=['data','realese'])

    def first_unanswered(self):
        return next(
            (
                step
                for step in self.steps()
                if not step.form_class(data=self.answer(step)).is_valid()
            ),
            None,
        )

    def is_ahead(self, step):
        pending = self.first_unanswered()
        steps = self.steps()
        return pending is not None and steps.index(step) > steps.index(pending)

    def number(self, step):
        return STEPS.index(step) + 1

    def sections(self, current):
        position = SECTIONS.index(current.section)
        return [
            {"name": name, "state": self.section_state(index, position)}
            for index, name in enumerate(SECTIONS)
        ]

    @staticmethod
    def section_state(index, position):
        if index < position:
            return "done"
        if index == position:
            return "current"
        return "pending"

    @transaction.atomic
    def complete(self, registered_by):
        values = {"registered_by": registered_by}
        if self.completed:
            self.draft.status='done'
            raise ValidationError("esse cadastro ja foi realizado,por favor faça outro")
        for step in self.steps():
            form = step.form_class(data=self.answer(step))
            if  form.is_valid():
                values.update(form.cleaned_data)
            else:
                raise ValidationError(f"{step.slug} inválido")

        # Preenche os campos do endereço que não são mais perguntados no mobile


        Patient(**values).full_clean(exclude=["password"])
        patient = Patient.objects.create_with_credentials(
            raw_data=values, created_by_user=registered_by
        )
        sincronizar_grupo(patient)
        self.draft.status='done'
        self.draft.save(update_fields=['status','realese'])


        return patient
