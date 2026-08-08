from django.urls import path
from . import views

app_name = "teacher"

urlpatterns = [
    path("", views.HomeProfessorView.as_view(), name="home"),
    path("painel/", views.PainelProfessorView.as_view(), name="painel"),
    path("cadastrar/", views.cadastrar_professor, name="cadastrar"),
    path("perfil/", views.PerfilProfessorView.as_view(), name="perfil"),
    path("vincular-aluno/", views.vincular_aluno, name="vincular_aluno"),
]