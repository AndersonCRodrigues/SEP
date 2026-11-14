from django.contrib.auth.models import Group
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from core.models import CustomUser
from .models import ServerStatus


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
