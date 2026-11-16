from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from core.fields import collapse_spaces
from core.managers import CustomUserManager
from core.models import CustomUser
from core.validators import validate_letters
from core.permissions import ALL, BusinessRulesMixin, RoleScopedQuerySet
from teacher.models import Teacher
from core.constants import VISIBLE_TO_AUTHOR
from utils.fields import EncryptedTextField


Role = CustomUser.Role

def with_open_case(prefix="", **lookups):
    caminho = f"{prefix}assignment_history"
    filtros = {f"{caminho}__end_date__isnull": True}
    filtros.update({f"{caminho}__{campo}": valor for campo, valor in lookups.items()})
    return Q(**filtros)

class PatientQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {
        Role.SUPERVISOR: ALL,
        Role.ADMINISTRATIVO: ALL,
        Role.PROFESSOR: lambda u: (
            with_open_case(student__current_advisor_id=u.pk)
            | Q(responsible_teachers=u.pk)
        ),
        Role.ALUNO: lambda u: (
            with_open_case(student_id=u.pk)
            | Q(
                triage_records__student_author_id=u.pk,
                triage_records__status__in=VISIBLE_TO_AUTHOR,
            )
        ),
        Role.PACIENTE: lambda u: Q(pk=u.pk),
    }

    def awaiting_triage(self):
        return self.filter(flow_status__in=("", Patient.FlowStatus.AWAITING_TRIAGE))

class PatientManager(CustomUserManager):
    @transaction.atomic
    def create_with_credentials(self,raw_data,created_by_user=None,commit=True):
        from patient.services import (
            build_first_access_url,
            create_first_access_invitation,
            send_first_access_sms,
        )

        patient_data = { **raw_data,"must_change_password": False}
        
        patient = self.model(**patient_data)
        patient.set_unusable_password()

        if not commit:
            return patient

        patient.save()

        invitation, token = create_first_access_invitation(patient)

        access_url = build_first_access_url(token)

        def send_after_commit():
            send_first_access_sms(invitation=invitation, access_url=access_url, responsible_user=created_by_user,)

        transaction.on_commit(send_after_commit)

        return patient

class Patient(BusinessRulesMixin, CustomUser):
    class FlowStatus(models.TextChoices):
        AWAITING_TRIAGE = "AGUARDANDO_TRIAGEM", "Aguardando triagem"
        IN_TRIAGE = "EM_TRIAGEM", "Em triagem"
        REFERRED = "ENCAMINHADO", "Encaminhado"
        AWAITING_REVIEW = "AWAITING_REVIEW", "Aguardando parecer"
        IN_TREATMENT = "IN_TREATMENT", "Em atendimento"
        DISCHARGED = "DISCHARGED", "Alta"

    flow_status = models.CharField(
        max_length=30,
        choices=FlowStatus.choices,
        default=FlowStatus.AWAITING_TRIAGE,
        blank=True,
        verbose_name="Status do fluxo",
    )
    social_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Nome social",
    )
    gender_identity = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Identidade de gênero",
    )
    race = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Cor/Raça",
    )
    naturalness = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Naturalidade",
    )
    schooling = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Escolaridade",
    )
    religion = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Religião",
    )
    marital_status = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Estado civil",
    )
    profession = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Profissão",
    )
    occupation = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        verbose_name="Ocupação atual",
    )

    ALLOWED_TRANSITIONS = {
        "": (FlowStatus.AWAITING_TRIAGE, FlowStatus.IN_TRIAGE, FlowStatus.IN_TREATMENT),
        FlowStatus.AWAITING_TRIAGE: (
            FlowStatus.IN_TRIAGE,
            FlowStatus.REFERRED,
        ),
        FlowStatus.IN_TRIAGE: (
            FlowStatus.AWAITING_REVIEW,
            FlowStatus.REFERRED,
        ),
        FlowStatus.AWAITING_REVIEW: (
            FlowStatus.IN_TRIAGE,
            FlowStatus.REFERRED,
        ),
        FlowStatus.REFERRED: (
            FlowStatus.IN_TRIAGE,
            FlowStatus.IN_TREATMENT,
        ),
        FlowStatus.IN_TREATMENT: (FlowStatus.DISCHARGED,),
        FlowStatus.DISCHARGED: (FlowStatus.AWAITING_TRIAGE, FlowStatus.IN_TRIAGE),
    }

    # ... [demais atributos e métodos continuam iguais] ...

    medical_record = EncryptedTextField(blank=True, verbose_name="Prontuário")

    responsible_teachers = models.ManyToManyField(
        Teacher,
        blank=True,
        related_name="referred_patients",
        verbose_name="Professores responsáveis",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    is_accompanied = models.BooleanField(
        null=True, blank=True, verbose_name="Está acompanhado"
    )

    guardian_first_name = models.CharField(
        max_length=150,
        blank=True,
        validators=[validate_letters],
        verbose_name="Nome do responsável",
    )

    guardian_last_name = models.CharField(
        max_length=150,
        blank=True,
        validators=[validate_letters],
        verbose_name="Sobrenome do responsável",
    )

    guardian_relationship = models.CharField(
        max_length=100,
        blank=True,
        validators=[validate_letters],
        verbose_name="Grau de parentesco",
    )

    registered_by = models.ForeignKey(
        CustomUser,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registered_patients",
        verbose_name="Cadastrado por",
    )

    # Usa o PatientManager preservando o PatientQuerySet do merge
    objects = PatientManager.from_queryset(PatientQuerySet)()

    REGISTRATION_FIELDS = (
        "first_name",
        "last_name",
        "cpf",
        "data_nascimento",
        "social_name",
        "gender_identity",
    ) + CustomUser.ADDRESS_FIELDS
    COMPLETION_FIELDS = ("data_nascimento",) + CustomUser.ADDRESS_FIELDS

    CREATABLE_BY = (Role.ADMINISTRATIVO,)
    EDITABLE_FIELDS = {
        Role.PROFESSOR: ("responsible_teachers",),
        Role.ADMINISTRATIVO: REGISTRATION_FIELDS,
        Role.ALUNO: COMPLETION_FIELDS,
        Role.PACIENTE: COMPLETION_FIELDS,
    }
    DELETABLE_BY = ()

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"

    # US-5.2: Cálculo dinâmico da idade atual
    @property
    def idade_atual(self):
        if not self.data_nascimento:
            return None
        hoje = timezone.localdate()
        nascimento = self.data_nascimento
        return (
            hoje.year
            - nascimento.year
            - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
        )

    # Alias mantido do código mesclado do outro dev
    @property
    def current_age(self):
        return self.idade_atual

    @property
    def active_treatment(self):
        return self.flow_status == self.FlowStatus.IN_TREATMENT

    def is_treated_by(self, student):
        return self.assignment_history.filter(
            student_id=student.pk, end_date__isnull=True
        ).exists()

    def advance_to(self, new_status):
        if new_status == self.flow_status:
            return False

        if new_status not in self.ALLOWED_TRANSITIONS.get(self.flow_status, ()):
            atual = self.get_flow_status_display() or "sem fluxo"
            destino = self.FlowStatus(new_status).label
            raise ValidationError(
                {"flow_status": f"Não é possível ir de {atual} para {destino}."}
            )

        with transaction.atomic():
            self.flow_status = new_status
            self.save(update_fields=["flow_status"])

            if new_status == self.FlowStatus.DISCHARGED:
                self.assignment_history.filter(end_date__isnull=True).update(
                    end_date=timezone.localdate()
                )
        return True

    def enforce_role(self):
        self.role = CustomUser.Role.PACIENTE

    def normalize(self):
        super().normalize()
        self.guardian_first_name = collapse_spaces(self.guardian_first_name)
        self.guardian_last_name = collapse_spaces(self.guardian_last_name)
        self.guardian_relationship = collapse_spaces(self.guardian_relationship)

    def __str__(self):
        return self.nome_completo

class FirstAcess(models.Model):
    class DeliveryStatus(models.TextChoices):
        PENDING = 'pending', "pendente"
        SENT = "sent", "Enviado"
        FAILED = "failed", "Falhou"
        SIMULATED = "simulated", "Simulado — sem envio real"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE,related_name="first_acess")
    token_hash = models.CharField(max_length=64,unique=True,editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    delivery_status = models.CharField(max_length=10, choices=DeliveryStatus.choices,default=DeliveryStatus.PENDING)