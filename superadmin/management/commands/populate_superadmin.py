import os
from django.core.management.base import BaseCommand

from core.models import CustomUser
from superadmin.models import ServerStatus, RolePermissionScope, BackupRecord

SERVIDORES_MOCK = [
    {"nome": "Servidor de triagem", "uptime_percent": "99.80", "cpu_percent": 11, "memoria_percent": 58, "health": ServerStatus.Health.SAUDAVEL},
    {"nome": "Servidor de aplicação", "uptime_percent": "98.20", "cpu_percent": 51, "memoria_percent": 76, "health": ServerStatus.Health.ATENCAO},
    {"nome": "Servidor de arquivos", "uptime_percent": "97.50", "cpu_percent": 32, "memoria_percent": 61, "health": ServerStatus.Health.SAUDAVEL},
    {"nome": "Banco de dados clínico", "uptime_percent": "99.70", "cpu_percent": 46, "memoria_percent": 44, "health": ServerStatus.Health.SAUDAVEL},
    {"nome": "Servidor de backup externo", "uptime_percent": "0.00", "cpu_percent": 0, "memoria_percent": 0, "health": ServerStatus.Health.OFFLINE},
]

ESCOPOS_MOCK = {
    CustomUser.Role.SUPERVISOR: "Triagens, encaminhamentos, professores",
    CustomUser.Role.PROFESSOR: "Prontuários da sua área, alunos",
    CustomUser.Role.ADMINISTRATIVO: "Agenda, salas, declarações",
    CustomUser.Role.ALUNO: "Triagem e prontuário sob supervisão",
}


class Command(BaseCommand):
    help = "Cria dados de demonstracao (mockados) para as telas do Superadmin."

    def handle(self, *args, **options):
        if os.getenv("NODE_ENV") != "dev":
            self.stdout.write(self.style.WARNING("Ignorado: só roda com NODE_ENV=dev."))
            return

        for dados in SERVIDORES_MOCK:
            ServerStatus.objects.update_or_create(nome=dados["nome"], defaults=dados)
        self.stdout.write(self.style.SUCCESS(f"{len(SERVIDORES_MOCK)} servidor(es) mockado(s)."))

        for role, escopo in ESCOPOS_MOCK.items():
            RolePermissionScope.objects.update_or_create(role=role, defaults={"escopo_acesso": escopo})
        self.stdout.write(self.style.SUCCESS(f"{len(ESCOPOS_MOCK)} escopo(s) de permissão criado(s)."))

        if not BackupRecord.objects.exists():
            BackupRecord.objects.create(escopo="Banco de dados clínico", tamanho="2.4 GB", status=BackupRecord.Status.CONCLUIDO)
            BackupRecord.objects.create(escopo="Infraestrutura completa", tamanho="11.8 GB", status=BackupRecord.Status.CONCLUIDO)
            BackupRecord.objects.create(escopo="Banco de dados clínico", status=BackupRecord.Status.AGENDADO)
            self.stdout.write(self.style.SUCCESS("3 registro(s) de backup criado(s)."))