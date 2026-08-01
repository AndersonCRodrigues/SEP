from django.urls import path
from . import views

app_name = "students"

urlpatterns = [
    path("", views.HomeEstudanteView.as_view(), name="home"),
    path("painel/", views.PainelEstudanteView.as_view(), name="painel"),
]