from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import ListView
from core.models import CustomUser


class SuperadminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        return (
            self.request.user.groups.filter(name="Superadmin").exists() 
            or self.request.user.is_superuser
        )


class PainelSuperadminView(SuperadminRequiredMixin, ListView):
    model = CustomUser
    template_name = "painel_superadmin.html"  
    context_object_name = "todos_usuarios"

    def get_queryset(self):
        return CustomUser.objects.all().order_by("-id")