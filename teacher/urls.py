from django.urls import path
from . import views

app_name = "teacher"   

urlpatterns = [
    path("", views.HomeProfessorView.as_view(), name="home"),
    path("painel/", views.PainelProfessorView.as_view(), name="painel"),
]