from django.urls import path
from . import views

urlpatterns = [
    path("minhas-triagens/", views.minhas_triagens, name="minhas_triagens"),
    path("fila/", views.fila_triagem, name="fila_triagem"),
    path("create/<int:patient_id>/", views.create_triage, name="create_triage"),
    path("submit/<int:pk>/", views.submit_triage, name="submit_triage"),
    path("feedback/<int:pk>/", views.create_feedback, name="create_feedback"),
    path("create_referral/<int:pk>/", views.create_referral, name="create_referral"),
    path("triage_detail/<int:pk>/", views.triage_detail, name="triage_detail"),
]