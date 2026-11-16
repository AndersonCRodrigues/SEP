from datetime import timedelta

from django.contrib.auth.models import Group
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import CustomUser

from .models import BackupRecord
from .views import BACKUP_LEVELS, BACKUP_TITLES

EXPECTED = {
    BackupRecord.Status.CONCLUIDO: (
        "Backup automático concluído",
        "Concluído",
        "success",
    ),
    BackupRecord.Status.AGENDADO: ("Backup agendado", "Agendado", "neutral"),
    BackupRecord.Status.FALHOU: ("Falha no backup", "Falhou", "danger"),
}


class BackupStatusMapTests(SimpleTestCase):
    def test_expected_table_covers_every_status(self):
        self.assertEqual(set(EXPECTED), set(BackupRecord.Status))

    def test_titles_and_levels_match_expected(self):
        for status, (title, _label, level) in EXPECTED.items():
            with self.subTest(status=status):
                self.assertEqual(BACKUP_TITLES[status], title)
                self.assertEqual(BACKUP_LEVELS[status], level)


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
        for index, status in enumerate(BackupRecord.Status, start=1):
            BackupRecord.objects.create(
                escopo=f"Escopo {index}", status=status, executado_em=when
            )

    @staticmethod
    def backup_activities(response):
        return {
            (a["title"], a["label"], a["level"])
            for a in response.context["activities"]
            if a["kind"] == "backup"
        }

    def test_home_shows_expected_title_and_badge_per_status(self):
        response = self.client.get(reverse("superadmin:home"))
        self.assertEqual(self.backup_activities(response), set(EXPECTED.values()))

    def test_backups_page_renders_expected_badge_per_record(self):
        response = self.client.get(reverse("superadmin:backups"))
        for row in response.context["rows"]:
            _title, label, level = EXPECTED[row["backup"].status]
            with self.subTest(escopo=row["backup"].escopo):
                self.assertEqual((row["label"], row["level"]), (label, level))
        for _title, label, _level in EXPECTED.values():
            self.assertContains(response, f'">{label}</span>')

    def test_unknown_status_does_not_break_screens(self):
        BackupRecord.objects.create(
            escopo="Escopo legado",
            status="XX",
            executado_em=timezone.now() + timedelta(minutes=10),
        )
        home = self.client.get(reverse("superadmin:home"))
        self.assertEqual(home.status_code, 200)
        self.assertIn(
            ("Backup com situação desconhecida", "XX", "neutral"),
            self.backup_activities(home),
        )
        backups = self.client.get(reverse("superadmin:backups"))
        self.assertEqual(backups.status_code, 200)
