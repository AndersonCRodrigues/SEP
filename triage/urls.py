from django.urls import path
from . import views


urlpatterns = [
    path(
        "create/<int:patient_id>/",
        views.create_triage,
        name="create_triage",
    ),
]
