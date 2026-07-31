from django.urls import path
from . import views

app_name = "students" 

urlpatterns = [
    path("", views.PainelEstudanteView.as_view(), name="painel"),
]