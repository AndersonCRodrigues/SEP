from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse

from core.models import CustomUser
from students.models import Advising, Student
from teacher.models import Teacher

SYNC_PATH = "students.views.account.sincronizar_grupo"
EMAIL_ALUNO = "novo.aluno@teste.com"
ENDERECO = {
    "telefone": "21999999999",
    "logradouro": "Rua de Teste",
    "number": "10",
    "complement": "",
    "bairro": "Centro",
    "municipality": "Maricá",
    "city": "Maricá",
    "state": "RJ",
    "cep": "24900-000",
}


def campos_do_modelo(model, dados):
    nomes = {campo.name for campo in model._meta.get_fields()}
    return {chave: valor for chave, valor in dados.items() if chave in nomes}


class CadastrarAlunoTransacaoTests(TestCase):
    def setUp(self):
        self.operador = CustomUser.objects.create_superuser(
            email="coordenador@teste.com",
            password="Senha@12345",  # nosec B106
            first_name="Coordenador",
            last_name="Teste",
            cpf="11144477735",
            **campos_do_modelo(CustomUser, ENDERECO),
        )
        self.client.force_login(self.operador)
        self.url = reverse("students:cadastrar")

    def dados_do_aluno(self, **extra):
        return {
            "email": EMAIL_ALUNO,
            "first_name": "Novo",
            "last_name": "Aluno",
            "cpf": "52998224725",
            "matricula": "2026001",
            "password1": "SenhaForte@2026",
            "password2": "SenhaForte@2026",
            **ENDERECO,
            **extra,
        }

    def post_com_falha_no_grupo(self, dados):
        with patch(SYNC_PATH, side_effect=DatabaseError("falha induzida")):
            return self.client.post(self.url, dados)

    def test_falha_no_grupo_nao_deixa_conta_parcial(self):
        resposta = self.post_com_falha_no_grupo(self.dados_do_aluno())

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "tente novamente")
        self.assertFalse(CustomUser.objects.filter(email=EMAIL_ALUNO).exists())
        self.assertFalse(Student.objects.filter(email=EMAIL_ALUNO).exists())

    def test_repetir_o_cadastro_depois_da_falha_funciona(self):
        dados = self.dados_do_aluno()
        self.post_com_falha_no_grupo(dados)

        resposta = self.client.post(self.url, dados)

        self.assertRedirects(
            resposta, reverse("supervisor:painel"), fetch_redirect_response=False
        )
        aluno = CustomUser.objects.get(email=EMAIL_ALUNO)
        self.assertTrue(aluno.groups.filter(name="Students").exists())

    def test_falha_no_grupo_desfaz_tambem_a_orientacao_inicial(self):
        professor = Teacher(
            email="professor@teste.com",
            first_name="Renata",
            last_name="Alves",
            cpf="39053344705",
            crp="05/10001",
            role=CustomUser.Role.PROFESSOR,
            **campos_do_modelo(Teacher, ENDERECO),
        )
        professor.set_password("Senha@12345")
        professor.save()
        dados = self.dados_do_aluno(current_advisor=professor.pk, periodo="2026.1")

        resposta = self.post_com_falha_no_grupo(dados)

        self.assertContains(resposta, "tente novamente")
        self.assertFalse(Advising.objects.filter(student__email=EMAIL_ALUNO).exists())
        self.assertFalse(Student.objects.filter(email=EMAIL_ALUNO).exists())
