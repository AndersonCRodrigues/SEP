from django.urls import path
from . import views

app_name = "administration"

urlpatterns = [
    path("", views.HomeAdministracaoView.as_view(), name="home"),
    path("painel/", views.PainelAdministracaoView.as_view(), name="painel"),
]