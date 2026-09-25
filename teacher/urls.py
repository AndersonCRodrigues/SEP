from django.urls import path
from . import views

app_name = "teacher"

urlpatterns = [
    path("", views.HomeProfessorView.as_view(), name="home"),
    path("painel/", views.PainelProfessorView.as_view(), name="painel"),
    path("prontuarios/", views.ProntuariosProfessorView.as_view(), name="prontuarios"),
    path("presenca/", views.PresencaProfessorView.as_view(), name="presenca"),
    path("area-atuacao/", views.AreaAtuacaoProfessorView.as_view(), name="area"),
    path("cadastrar/", views.cadastrar_professor, name="cadastrar"),
    path("perfil/", views.PerfilProfessorView.as_view(), name="perfil"),
    path("vincular-aluno/", views.vincular_aluno, name="vincular_aluno"),
    path("lancar-horas/", views.lancar_horas, name="lancar_horas"),
    path("triagem/atribuir/", views.TeacherAssignTriageView.as_view(), name="assign_triage"),
]
