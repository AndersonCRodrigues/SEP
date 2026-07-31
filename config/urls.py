from django.contrib import admin
from django.urls import path, include
from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    
    path("", core_views.home, name="home"),
    path("cadastro/", core_views.cadastrar_usuario, name="cadastro"),
    path("login/", core_views.CustomLoginView.as_view(), name="login"),
    path("logout/", core_views.CustomLogoutView.as_view(), name="logout"),
    path("area/", core_views.area_usuario, name="area_usuario"),

    path("administration/", include("administration.urls")),
    path("students/", include("students.urls")),
    path("professors/", include("professors.urls")),
    path("supervisor/", include("supervisor.urls")),
    path("superadmin/", include("superadmin.urls")),
]