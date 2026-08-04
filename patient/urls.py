from django.urls import path
from . import views

app_name = "patient"

urlpatterns = [
    path("", views.HomePacienteView.as_view(), name="home"),
    path("edit/", views.EditarDadosPacienteView.as_view(), name="edit_data"),
]