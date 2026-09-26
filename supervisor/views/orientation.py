from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from core.constants import TriageStatus
from core.mixins import GroupRequiredMixin
from students.models import Student
from teacher.forms import StudentActivityForm, VincularAlunoForm
from teacher.models import Teacher
from triage.models import Referral, TriageRecord


class PainelOrientacaoSupervisorView(GroupRequiredMixin, TemplateView):
    """
    Painel de orientação/encaminhamentos do Supervisor — separado do
    PainelProfessorView (que é só-Professor) porque o Supervisor tem
    acesso geral (todos os alunos vinculados, todas as triagens pendentes,
    histórico completo, todos os encaminhamentos).
    """

    required_group = "Supervisor"
    template_name = "supervisor/orientacao_panel.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supervisor = get_object_or_404(Teacher, pk=self.request.user.pk)

        context["alunos_vinculados"] = Student.objects.filter(
            current_advisor__isnull=False
        )
        context["alunos_disponiveis"] = Student.objects.filter(
            current_advisor__isnull=True
        )
        # Triagens já submetidas pelo Aluno, esperando parecer/encaminhamento.
        context["triagens_pendentes"] = TriageRecord.objects.visible_to(
            self.request.user
        ).filter(status=TriageStatus.SUBMITTED)
        # Histórico: triagens que já saíram do "aguardando parecer" — já
        # encaminhadas ou já fechadas.
        context["historico_triagens"] = (
            TriageRecord.objects.visible_to(self.request.user)
            .exclude(status__in=[TriageStatus.OPEN, TriageStatus.SUBMITTED])
            .order_by("-created_at")
        )
        context["todos_encaminhamentos"] = Referral.objects.visible_to(
            self.request.user
        )
        context["form_vincular"] = VincularAlunoForm()
        context["form_horas"] = StudentActivityForm(user=supervisor)
        return context
