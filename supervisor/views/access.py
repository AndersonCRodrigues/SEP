from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from core.models import CustomUser


class CoordinatorOnly(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == CustomUser.Role.SUPERVISOR
