from django.urls import path
from . import views

app_name = "professors"

urlpatterns = [
    path("", views.PainelProfessorView.as_view(), name="painel"),
]