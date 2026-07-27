from django.contrib import admin
from django.urls import path
from core import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.cadastrar_usuario, name="cadastro"),
    path("area/", views.area_usuario, name="area_usuario"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("usuarios/", views.ListarUsuariosView.as_view(), name="listar_usuarios"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("painel-professor/", views.painel_professor, name="painel_professor"),
    path("painel-supervisor/", views.PainelSupervisor.as_view(), name="painel_supervisor"),
]