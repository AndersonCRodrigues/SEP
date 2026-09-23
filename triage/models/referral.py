from core.permissions import ALL, BusinessRulesMixin, RoleScopedQuerySet
from django.db import models, transaction
from areas.models import AreaActing
from patient.models.patient import Patient
from .triage_record import TriageRecord
from teacher.models import Teacher
from core.models import CustomUser
from django.db.models import Q
from core.constants import TriageStatus
from django.core.exceptions import ValidationError



Role=CustomUser.Role



class ReferralQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {
        Role.SUPERVISOR:ALL,
        Role.PROFESSOR: lambda u:Q(area__in=u.acting_areas.all()),
        Role.ALUNO: lambda u:Q(triage__student_author_id=u.pk)
        
    }

class Referral(BusinessRulesMixin,models.Model):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="encaminhamento_paciente",
        verbose_name="encaminhamento de triagem do paciente"
    )

    area=models.ManyToManyField(AreaActing)
    
    
    triage = models.ForeignKey(
        TriageRecord,
        on_delete=models.PROTECT,
        related_name="triagem_encaminhando",
        verbose_name="triagem encaminhando", 
    )
    
    coordinator = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name="Supervisor_responsavel",
        verbose_name="Supervisor responsável pelo encaminhamento"
    )
    
    objects = ReferralQuerySet.as_manager()
    
    CREATABLE_BY = (Role.SUPERVISOR,)
    EDITABLE_FIELDS = {}
    DELETABLE_BY = ()
    
    def save(self,*args,**kwargs):
        if self.patient!=self.triage.patient:
            raise ValidationError(
                f"O nome do paciente da triage {self.triage.patient} não condiz com {self.patient}"
                )
        with transaction.atomic():
            super().save(*args,**kwargs)
            self.triage.status=TriageStatus.REFERRED
            self.triage.save()
            
            
    @classmethod
    def can_be_created_by(cls, user,triage=None, **context):
         if not super().can_be_created_by(user):
            return False
         if triage and triage.status in (TriageStatus.SUBMITTED, TriageStatus.FINALIZED_EDITION):
            return True
         else:
             return False
    
    def __str__(self):
        areas = ", ".join(a.nome for a in self.area.all())
        return f"O paciente {self.triage.patient.nome_completo} foi encaminhado para a area de atuação {areas}"