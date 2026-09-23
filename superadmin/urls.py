from django.urls import path
from . import views

app_name = "superadmin"

urlpatterns = [
    path("", views.HomeSuperadminView.as_view(), name="home"),
    path("perfil/", views.PerfilSuperadminView.as_view(), name="perfil"),
    path("servidores/", views.ServerStatusView.as_view(), name="servidores"),
    path("logs/", views.SecurityLogView.as_view(), name="logs"),
    path("logs/<int:pk>/", views.SecurityLogDetailView.as_view(), name="log_detail"),
    
    path("permissoes/", views.RolePermissionScopeView.as_view(), name="permissoes"),
    path("permissoes/<int:pk>/editar/", views.RolePermissionScopeUpdateView.as_view(), name="permissao_editar"),
    path("backups/", views.BackupListView.as_view(), name="backups"),
]
