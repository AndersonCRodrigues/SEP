from django.urls import path
from django.views.generic import TemplateView
from django.conf import settings
from . import views


urlpatterns = [
    path(
        "create/<int:patient_id>/",
        views.create_triage,
        name="create_triage",
    ),
]

# Rota exclusiva para testes de UI da equipe de front-end, apenas em ambiente de desenvolvimento (DEBUG)
if settings.DEBUG:
    urlpatterns += [
        path(
            "ui-test/form/",
            TemplateView.as_view(template_name="triage/create_triage.html"),
            name="ui_test_triage_form",
        ),
        path(
            "ui-test/success/",
            TemplateView.as_view(template_name="triage/triage_success.html"),
            name="ui_test_triage_success",
        ),
    ]
