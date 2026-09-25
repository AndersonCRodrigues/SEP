from django.utils import timezone
from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView, UpdateView, DetailView
from core.models import CustomUser
from core.mixins import GroupRequiredMixin
from django.db.models import Q
from audit.models import SecurityLog
from .models import ServerStatus, RolePermissionScope, BackupRecord

class HomeSuperadminView(GroupRequiredMixin, TemplateView):
    required_group = "Superadmin"
    template_name = "superadmin/home_superadmin.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["active_users"] = CustomUser.objects.filter(is_active=True).count()

        today_start = timezone.localtime(timezone.now()).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        context["logs_today"] = SecurityLog.objects.filter(created_at__gte=today_start).count()

        servers_needing_attention = ServerStatus.objects.filter(health=ServerStatus.Health.ATENCAO)
        context["open_alerts"] = servers_needing_attention.count()
        alert_server = servers_needing_attention.first()
        context["alert_server"] = alert_server
        context["alert_message"] = (
            f"CPU do {alert_server.nome} em {alert_server.cpu_percent}%"
            if alert_server else ""
        )

        recent_activities = []
        for backup in BackupRecord.objects.all()[:3]:
            recent_activities.append({
                "kind": "backup",
                "title": "Backup automático concluído" if backup.status == BackupRecord.Status.CONCLUIDO else "Backup agendado",
                "detail": backup.escopo,
                "when": backup.executado_em or backup.agendado_para,
                "status": backup.get_status_display(),
            })
        for log in SecurityLog.objects.all()[:3]:
            recent_activities.append({
                "kind": "security",
                "title": log.get_action_display(),
                "detail": log.detail or log.user_identifier or "",
                "when": log.created_at,
                "status": None,
            })
        recent_activities.sort(key=lambda item: item["when"] or timezone.now(), reverse=True)
        context["recent_activities"] = recent_activities[:5]

        return context


class PerfilSuperadminView(GroupRequiredMixin, UpdateView):
    required_group = "Superadmin"
    model = CustomUser
    template_name = "superadmin/perfil.html"
    success_url = reverse_lazy("superadmin:perfil")

    def get_object(self, queryset=None):
        return self.request.user


class ServerStatusView(GroupRequiredMixin, ListView):
    required_group = "Superadmin"
    model = ServerStatus
    template_name = "superadmin/server_status.html"
    context_object_name = "servidores"


class SecurityLogView(GroupRequiredMixin, ListView):
    required_group = "Superadmin"
    model = SecurityLog
    template_name = "superadmin/security_logs.html"
    context_object_name = "logs"
    paginate_by = 20

    SEVERIDADE_POR_ACTION = {
        SecurityLog.Action.LOGIN_FAILED: "critico",
        SecurityLog.Action.ACCESS_DENIED: "critico",
        SecurityLog.Action.ROLE_CHANGE: "atencao",
        SecurityLog.Action.PERMISSION_CHANGE: "atencao",
        SecurityLog.Action.DELETE: "atencao",
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        termo = self.request.GET.get("q", "").strip()
        if termo:
            queryset = queryset.filter(
                Q(detail__icontains=termo) | Q(user_identifier__icontains=termo)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for log in context["logs"]:
            log.severidade = self.SEVERIDADE_POR_ACTION.get(log.action, "info")
        return context

class SecurityLogDetailView(GroupRequiredMixin, DetailView):
    required_group = "Superadmin"
    model = SecurityLog
    template_name = "superadmin/security_log_detail.html"
    context_object_name = "log"

class RolePermissionScopeView(GroupRequiredMixin, ListView):
    required_group = "Superadmin"
    model = RolePermissionScope
    template_name = "superadmin/role_permissions.html"
    context_object_name = "escopos"


class RolePermissionScopeUpdateView(GroupRequiredMixin, UpdateView):
    required_group = "Superadmin"
    model = RolePermissionScope
    fields = ["escopo_acesso"]
    template_name = "superadmin/role_permission_form.html"
    success_url = reverse_lazy("superadmin:permissoes")


class BackupListView(GroupRequiredMixin, ListView):
    required_group = "Superadmin"
    model = BackupRecord
    template_name = "superadmin/backups.html"
    context_object_name = "backups"