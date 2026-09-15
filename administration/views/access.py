from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from core.models import CustomUser
from documents.models import AttendanceCertificate
from patient.models import Patient


class AdministrativeOnly(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == CustomUser.Role.ADMINISTRATIVO


class CanRegisterPatients(AdministrativeOnly):
    def test_func(self):
        return super().test_func() and Patient.can_be_created_by(self.request.user)


class CanIssueCertificates(AdministrativeOnly):
    def test_func(self):
        return super().test_func() and AttendanceCertificate.can_be_created_by(
            self.request.user
        )
