from django.urls import path
from . import views

app_name = "administration"

urlpatterns = [
    # Mude de views.HomeAdministracaoView para views.PainelAdministracaoView
    path("", views.PainelAdministracaoView.as_view(), name="home"),
    path("painel/", views.PainelAdministracaoView.as_view(), name="painel"),
    path("cadastrar/", views.cadastrar_administrativo, name="cadastrar"),
    path("perfil/", views.PerfilAdministrativoView.as_view(), name="perfil"),
    path("cadastrar-paciente/", views.cadastrar_paciente, name="cadastrar_paciente"),
]
