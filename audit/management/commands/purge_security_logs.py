from django.core.management.base import BaseCommand

from audit.models import SecurityLog


class Command(BaseCommand):
    help = f"Apaga logs de segurança com mais de {SecurityLog.RETENTION_DAYS} dias."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Apenas informa quantos registros seriam apagados.",
        )

    def handle(self, *args, **options):
        expired = SecurityLog.objects.expired()
        total = expired.count()

        if options["dry_run"]:
            self.stdout.write(
                f"{total} registro(s) fora da retenção de "
                f"{SecurityLog.RETENTION_DAYS} dias. Nada foi apagado."
            )
            return

        if not total:
            self.stdout.write(self.style.SUCCESS("Nenhum log expirado."))
            return

        expired.delete()
        self.stdout.write(
            self.style.SUCCESS(f"{total} log(s) de segurança removido(s).")
        )
