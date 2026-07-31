from django.urls import path
from . import views

app_name = "supervisor"

urlpatterns = [
    path("", views.PainelSupervisorView.as_view(), name="painel"),
    path("usuarios/", views.ListarUsuariosView.as_view(), name="listar_usuarios"), 
]