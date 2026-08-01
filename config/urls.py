from django.contrib import admin
from django.urls import path, include
from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", core_views.RedirecionarHomeView.as_view(), name="home_redirect"),
    path("login/", core_views.CustomLoginView.as_view(), name="login"),
    path("logout/", core_views.CustomLogoutView.as_view(), name="logout"),

    path("administration/", include("administration.urls")),
    path("students/", include("students.urls")),
    path("teacher/", include("teacher.urls")),
    path("supervisor/", include("supervisor.urls")),
    path("superadmin/", include("superadmin.urls")),
    path("patient/", include("patient.urls")),
]