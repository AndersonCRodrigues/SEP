from django.urls import path
from . import views

app_name = "supervisor"

urlpatterns = [
    path("", views.HomeSupervisorView.as_view(), name="home"),
    path("painel/", views.PainelSupervisorView.as_view(), name="painel"),
    path("usuarios/", views.ListarUsuariosView.as_view(), name="listar_usuarios"),
    path("register/", views.cadastrar_usuario, name="register"),
]