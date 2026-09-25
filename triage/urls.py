from django.conf import settings
from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "triage"


urlpatterns = [
    path("minhas-triagens/", views.minhas_triagens, name="minhas_triagens"),
    path("fila/", views.fila_triagem, name="fila_triagem"),
    path("create/<int:patient_id>/", views.create_triage_start, name="create_triage"),
    path(
        "create/<int:patient_id>/<slug:step>/",
        views.create_triage_step,
        name="create_triage_step",
    ),
    path("concluida/<int:pk>/", views.triagem_concluida, name="triagem_concluida"),
    path("edit/<int:pk>/", views.edit_triage, name="edit_triage"),
    path("submit/<int:pk>/", views.submit_triage, name="submit_triage"),
    path("feedback/<int:pk>/", views.create_feedback, name="create_feedback"),
    path("create_referral/<int:pk>/", views.create_referral, name="create_referral"),
    # Rotas separadas por Role
    path(
        "student_detail/<int:pk>/",
        views.triage_detail_student,
        name="triage_detail_student",
    ),
    path(
        "supervisor_detail/<int:pk>/",
        views.triage_detail_supervisor,
        name="triage_detail_supervisor",
    ),
    path(
        "lock_triage_editing/<int:pk>/",
        views.lock_triage_editing,
        name="lock_triage_editing",
    ),
]

# Rotas exclusivas para teste de UI do front, apenas com DEBUG. O formulário
# único do front fica aqui, convivendo com o passo a passo das rotas acima.
if settings.DEBUG:
    urlpatterns += [
        path(
            "ui-test/form/",
            TemplateView.as_view(template_name="triage/create_triage_ui.html"),
            name="ui_test_triage_form",
        ),
        path(
            "ui-test/success/",
            TemplateView.as_view(template_name="triage/triage_success.html"),
            name="ui_test_triage_success",
        ),
    ]
