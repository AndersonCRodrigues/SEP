from django.contrib.auth.mixins import UserPassesTestMixin


class GroupRequiredMixin(UserPassesTestMixin):
    required_group = None

    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        if self.required_group is None:
            raise NotImplementedError(
                "Defina 'required_group' na subclasse de GroupRequiredMixin."
            )
        return (
            self.request.user.groups.filter(name=self.required_group).exists()
            or self.request.user.is_superuser
        )