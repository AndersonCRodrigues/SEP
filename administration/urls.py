from django.urls import path
from . import views

app_name = "administration" # Ajustado para bater com o nome da pasta e template

urlpatterns = [
    path("", views.PainelAdministracaoView.as_view(), name="painel"),
]