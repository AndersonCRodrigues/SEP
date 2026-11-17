from datetime import timedelta

from django.contrib.auth.models import Group
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import CustomUser

from .models import BackupRecord, ServerStatus
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


def login_superadmin(client):
    user = CustomUser.objects.create_user(
        email="ti@sep.test",
        password="senha-de-teste",  # nosec B106
        first_name="Equipe",
        last_name="TI",
        role=CustomUser.Role.SUPERADMIN,
    )
    user.groups.add(Group.objects.get_or_create(name="Superadmin")[0])
    client.force_login(user)


def make_server(**fields):
    data = {
        "nome": "Servidor X",
        "uptime_percent": 99,
        "cpu_percent": 10,
        "memoria_percent": 10,
        "health": ServerStatus.Health.ATENCAO,
    }
    return ServerStatus(**{**data, **fields})


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
        login_superadmin(self.client)
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


class ServerAlertMessageTests(SimpleTestCase):
    def test_offline_reports_unavailability(self):
        server = make_server(health=ServerStatus.Health.OFFLINE)
        self.assertEqual(
            server.alert_message(), "Servidor X indisponível, sem resposta."
        )

    def test_attention_by_memory(self):
        server = make_server(memoria_percent=ServerStatus.MEMORY_LIMIT_PERCENT + 1)
        self.assertEqual(
            server.metrics_over_limit(), [("Memória", server.memoria_percent)]
        )

    def test_attention_by_cpu(self):
        server = make_server(cpu_percent=ServerStatus.CPU_LIMIT_PERCENT + 1)
        self.assertEqual(server.metrics_over_limit(), [("CPU", server.cpu_percent)])

    def test_attention_without_metric_is_neutral(self):
        self.assertEqual(make_server().alert_message(), "Servidor X em atenção.")


class HomeAlertTests(TestCase):
    def setUp(self):
        login_superadmin(self.client)

    def home(self):
        return self.client.get(reverse("superadmin:home")).context

    @staticmethod
    def open_alerts(context):
        return next(
            i["value"] for i in context["indicators"] if i["label"] == "Alertas abertos"
        )

    def test_offline_alone_is_counted_and_shown(self):
        make_server(nome="Saudável", health=ServerStatus.Health.SAUDAVEL).save()
        make_server(nome="Fora do ar", health=ServerStatus.Health.OFFLINE).save()
        context = self.home()
        self.assertEqual(self.open_alerts(context), 1)
        self.assertEqual(context["alert_server"].nome, "Fora do ar")
        self.assertEqual(
            context["alert_message"], "Fora do ar indisponível, sem resposta."
        )

    def test_offline_has_priority_over_attention(self):
        make_server(nome="A em atenção").save()
        make_server(nome="Z fora do ar", health=ServerStatus.Health.OFFLINE).save()
        context = self.home()
        self.assertEqual(self.open_alerts(context), 2)
        self.assertEqual(context["alert_server"].nome, "Z fora do ar")
        self.assertEqual(
            context["alert_message"], "Z fora do ar indisponível, sem resposta."
        )

    def test_all_healthy_keeps_no_alert(self):
        make_server(health=ServerStatus.Health.SAUDAVEL).save()
        context = self.home()
        self.assertEqual(self.open_alerts(context), 0)
        self.assertIsNone(context["alert_server"])
        self.assertEqual(context["alert_message"], "Nenhum alerta ativo no momento.")
