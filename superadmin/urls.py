from django.urls import path
from . import views

app_name = "superadmin"

urlpatterns = [
    path("", views.HomeSuperadminView.as_view(), name="home"),
    path("painel/", views.PainelSuperadminView.as_view(), name="painel"),
]