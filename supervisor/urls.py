from django.urls import path
from . import views

app_name = "supervisor"

urlpatterns = [
    path("", views.HomeSupervisorView.as_view(), name="home"),
    path("painel/", views.PainelSupervisorView.as_view(), name="painel"),
    path("usuarios/", views.ListarUsuariosView.as_view(), name="listar_usuarios"),
    path("register/", views.cadastrar_supervisor, name="register"),
    path("areas/", views.ListaAreasView.as_view(), name="areas"),
    path("areas/nova/", views.CriarAreaView.as_view(), name="area_criar"),
    path("areas/<int:pk>/editar/", views.EditarAreaView.as_view(), name="area_editar"),
]