from django.urls import path
from . import views

app_name = "patient"

urlpatterns = [
    path("", views.PatientHomeView.as_view(), name="home"),
    path("edit/", views.EditarDadosPacienteView.as_view(), name="edit_data"),
    path("agendamentos/", views.PatientAppointmentsView.as_view(), name="agendamentos"),
    path(
        "agendamentos/solicitar/",
        views.AppointmentRequestView.as_view(),
        name="solicitar_horario",
    ),
    path("historico/", views.PatientHistoryView.as_view(), name="historico"),
    path(
        "historico/<int:pk>/",
        views.PatientSessionDetailView.as_view(),
        name="historico_detalhe",
    ),
    path("triagens/", views.PatientTriagesView.as_view(), name="triagens"),
    path(
        "triagens/<int:pk>/",
        views.PatientTriageDetailView.as_view(),
        name="triagem_detalhe",
    ),
    path("contato/", views.PatientContactView.as_view(), name="contato"),
]
