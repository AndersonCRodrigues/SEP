from datetime import timedelta

from django.contrib.auth.models import Group
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import CustomUser

from .models import BackupRecord
from .views import BACKUP_LEVELS, BACKUP_TITLES


class BackupStatusMapTests(SimpleTestCase):
    def test_every_status_has_title_and_level(self):
        for status in BackupRecord.Status:
            self.assertIn(status, BACKUP_TITLES)
            self.assertIn(status, BACKUP_LEVELS)


class BackupStatusScreensTests(TestCase):
    def setUp(self):
        user = CustomUser.objects.create_user(
            email="ti@sep.test",
            password="senha-de-teste",  # nosec B106
            first_name="Equipe",
            last_name="TI",
            role=CustomUser.Role.SUPERADMIN,
        )
        user.groups.add(Group.objects.get_or_create(name="Superadmin")[0])
        self.client.force_login(user)
        when = timezone.now() + timedelta(minutes=5)
        for status in BackupRecord.Status:
            BackupRecord.objects.create(
                escopo=f"Escopo {status.label}", status=status, executado_em=when
            )

    def backup_activities(self):
        response = self.client.get(reverse("superadmin:home"))
        return [a for a in response.context["activities"] if a["kind"] == "backup"]

    def test_home_shows_one_title_per_status(self):
        titles = [a["title"] for a in self.backup_activities()]
        self.assertCountEqual(titles, BACKUP_TITLES.values())

    def test_failed_backup_is_not_shown_as_scheduled(self):
        failed = next(
            a
            for a in self.backup_activities()
            if a["title"] == BACKUP_TITLES[BackupRecord.Status.FALHOU]
        )
        self.assertEqual((failed["label"], failed["level"]), ("Falhou", "danger"))

    def test_backups_page_shows_every_status_label(self):
        response = self.client.get(reverse("superadmin:backups"))
        for status in BackupRecord.Status:
            self.assertContains(response, status.label)
