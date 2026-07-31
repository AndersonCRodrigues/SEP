from django.urls import path
from . import views

app_name = "superadmin"

urlpatterns = [
    path("", views.PainelSuperadminView.as_view(), name="painel"),
]