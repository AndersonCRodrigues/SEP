from django.urls import path
from . import views

app_name = "students"

urlpatterns = [
    path("", views.HomeEstudanteView.as_view(), name="home"),
    path("painel/", views.HomeEstudanteView.as_view(), name="painel"),
    path("cadastrar/", views.cadastrar_aluno, name="cadastrar"),
    path("perfil/", views.PerfilAlunoView.as_view(), name="perfil"),
    path("meu-professor/", views.MeuProfessorView.as_view(), name="meu_professor"),
]