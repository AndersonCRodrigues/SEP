'''
Refs.:
https://docs.djangoproject.com/en/6.0/howto/custom-management-commands/
'''
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from core.models import CustomUser

class Command(BaseCommand):
    help = 'Popula o banco de dados com usuários de teste para as Roles selecionadas.' # E printado no terminal se colocado 'docker compose exec django-web python3 manage.py popular_usuarios --help'

    def add_arguments(self, parser): 
        #Permite passar roles como argumentos separados por espaço. ex.: --roles PR AL
        parser.add_argument(
            '--roles',
            nargs='+',
            type=str,
            choices=[role[0] for role in CustomUser.Role.choices],
            help='Especifica quais roles criar (SA SV PR AD AL). Se não for passado, cria uma de cada.'
        )# Decidi fazer desse jeito para ser mais pratico se quisermos testar so 1 tipo de role

    def handle(self, *args, **options):
        roles_selecionadas = options['roles']

        if not roles_selecionadas: # Se nenhum role foi passada, seleciona todas
            roles_selecionadas = [role[0] for role in CustomUser.Role.choices]
        
        #Dicionario com cpfs validos por role
        cpfs_validos = {
            'SA': '372.530.470-01',
            'SV': '876.681.090-64',
            'PR': '150.668.070-47',
            'AD': '071.466.920-27',
            'AL': '155.118.510-51',
        }

        for role in roles_selecionadas:
            email = f"{role.lower()}@teste.com"

            if CustomUser.objects.filter(email=email).exists():
                self.stdout.write(self.style.WARNING(f"Usuário: {role} ({email}) já existe."))
            
            user = CustomUser(
                email=email,
                nome_completo=f"Usuario Teste {role}",
                cpf=cpfs_validos[role],
                telefone="(99) 99999-9999",
                logradouro="Rua de Teste",
                numero="0",
                bairro="Centro",
                cidade="Maricá",
                estado="RJ",
                cep="24900-000",
                role=role
            )

            if role == CustomUser.Role.ALUNO:
                user.matricula = "20261001"
            elif role in (CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR):
                user.crp = f"12345/RJ-{role}"
            
            if role == CustomUser.Role.SUPERADMIN:
                user.is_staff = True
                user.is_superuser = True
            
            user.set_password("SenhaForte123!")

            try:
                # O .full_clean() força a chamada da função clean() que você declarou no models.py
                user.full_clean() 
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Usuário {role} ({email}) criado com sucesso!"))
            except ValidationError as e:
                self.stdout.write(self.style.ERROR(f"Erro de validação no usuário {role}: {e}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Erro inesperado no usuário {role}: {e}"))