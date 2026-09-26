from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import TemplateView

from areas.models import AreaActing
from core.constants import TriageStatus
from core.models import CustomUser
from patient.models import Patient
from teacher.models import Teacher
from triage.models import TriageRecord

from .access import CoordinatorOnly
from .triages import received_label

CONCLUDED = (TriageStatus.SUBMITTED, TriageStatus.CLOSED)
CONCLUDED_LIMIT = 10
RECENT_LIMIT = 6


class CoordinatorReferralsView(CoordinatorOnly, TemplateView):
    template_name = "supervisor/encaminhamentos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.localtime()
        triagem = self.selected_triage(user)
        area = self.request.GET.get("area", "")

        context["triagens"] = [
            {
                "triage": record,
                "patient": record.patient.get_full_name(),
                "student": record.student_author.get_full_name(),
                "received": received_label(record.created_at, now),
                "selected": triagem is not None and record.pk == triagem.pk,
            }
            for record in self.concluded(user)[:CONCLUDED_LIMIT]
        ]
        context["triagem"] = triagem
        context["areas"] = AreaActing.objects.order_by("nome")
        context["area_filter"] = area
        context["teachers"] = self.teachers(area)
        context["chosen"] = (
            set(triagem.patient.responsible_teachers.values_list("pk", flat=True))
            if triagem
            else set()
        )
        context["recent"] = self.recent(user)
        return context

    def post(self, request, *args, **kwargs):
        triagem = self.selected_triage(request.user)
        if triagem is None:
            messages.error(request, "Escolha a triagem do paciente a encaminhar.")
            return redirect("supervisor:encaminhamentos")

        escolhidos = Teacher.objects.filter(
            role=CustomUser.Role.PROFESSOR, pk__in=request.POST.getlist("professores")
        )
        if not escolhidos:
            messages.error(request, "Escolha ao menos um professor para encaminhar.")
            return redirect("supervisor:encaminhar", pk=triagem.pk)

        try:
            self.refer(triagem, escolhidos, request.user)
        except ValidationError as erro:
            messages.error(request, erro.messages[0])
            return redirect("supervisor:encaminhar", pk=triagem.pk)

        messages.success(
            request,
            f"{triagem.patient.get_full_name()} encaminhado para {escolhidos.count()} professor(es).",
        )
        return redirect("supervisor:encaminhamentos")

    @staticmethod
    def concluded(user):
        return (
            TriageRecord.objects.visible_to(user)
            .filter(status__in=CONCLUDED)
            .select_related("patient", "student_author")
            .order_by("-created_at")
        )

    @staticmethod
    def teachers(area):
        professores = Teacher.objects.filter(
            role=CustomUser.Role.PROFESSOR
        ).prefetch_related("acting_areas")

        if area.isdigit():
            professores = professores.filter(acting_areas__pk=area)

        return professores.distinct().order_by("first_name", "last_name")

    def selected_triage(self, user):
        if self.kwargs.get("pk"):
            return get_object_or_404(self.concluded(user), pk=self.kwargs["pk"])

        return self.concluded(user).first()

    @staticmethod
    @transaction.atomic
    def refer(triagem, professores, user):
        paciente = triagem.patient
        paciente.responsible_teachers.set(professores)

        triagem.status = TriageStatus.REFERRED
        triagem.closed_by = user
        triagem.closed_at = timezone.now()
        triagem.save()

    @staticmethod
    def recent(user):
        encaminhadas = (
            TriageRecord.objects.visible_to(user)
            .filter(status=TriageStatus.REFERRED)
            .select_related("patient")
            .prefetch_related("patient__responsible_teachers")
            .order_by("-closed_at")[:RECENT_LIMIT]
        )

        linhas = []
        for record in encaminhadas:
            paciente = record.patient
            professores = ", ".join(
                professor.get_full_name()
                for professor in paciente.responsible_teachers.all()
            )
            concluido = paciente.flow_status == Patient.FlowStatus.IN_TREATMENT
            linhas.append(
                {
                    "patient": paciente.get_full_name(),
                    "teachers": professores or "Aguardando",
                    "label": "Concluído" if concluido else "Pendente",
                    "level": "success" if concluido else "warning",
                }
            )
        return linhas
