from django.urls import path
from . import views

app_name = "administration"

urlpatterns = [
    path("", views.AdministrativeHomeView.as_view(), name="home"),
    path("painel/", views.PainelAdministracaoView.as_view(), name="painel"),
    path("cadastrar/", views.cadastrar_administrativo, name="cadastrar"),
    path("perfil/", views.PerfilAdministrativoView.as_view(), name="perfil"),
    path("cadastrar-paciente/", views.cadastrar_paciente, name="cadastrar_paciente"),
    path("pacientes/", views.PatientsView.as_view(), name="pacientes"),
    path("agenda/", views.ScheduleView.as_view(), name="agenda"),
    path("salas/", views.RoomsView.as_view(), name="salas"),
    path("declaracoes/", views.DeclarationsView.as_view(), name="declaracoes"),
    path("atestados/", views.CertificatesView.as_view(), name="atestados"),
]
