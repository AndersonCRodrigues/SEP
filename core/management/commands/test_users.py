'''
Refs.:
https://docs.djangoproject.com/en/6.0/howto/custom-management-commands/
'''
import random
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from core.models import CustomUser

def gerar_cpf_valido():
    """Gera um CPF matematicamente válido para burlar a validação em ambiente de teste."""
    cpf = [random.randint(0, 9) for _ in range(9)]
    
    soma1 = sum(x * y for x, y in zip(cpf, range(10, 1, -1)))
    d1 = 11 - (soma1 % 11)
    d1 = 0 if d1 >= 10 else d1
    cpf.append(d1)
    
    soma2 = sum(x * y for x, y in zip(cpf, range(11, 1, -1)))
    d2 = 11 - (soma2 % 11)
    d2 = 0 if d2 >= 10 else d2
    cpf.append(d2)
    
    return f"{cpf[0]}{cpf[1]}{cpf[2]}.{cpf[3]}{cpf[4]}{cpf[5]}.{cpf[6]}{cpf[7]}{cpf[8]}-{cpf[9]}{cpf[10]}"

class Command(BaseCommand):
    help = 'Popula o banco de dados com usuários de teste para as Roles selecionadas.' # E printado no terminal se colocado 'docker compose exec django-web python3 manage.py test_user --help'

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
        
        for role in roles_selecionadas:
            prefixo = role.lower()
            email = f"{prefixo}@teste.com"
            contador = 1

            while CustomUser.objects.filter(email=email).exists():
                email = f"{prefixo}{contador}@teste.com"
                contador += 1
            
            cpf_dinamico = gerar_cpf_valido()

            user = CustomUser(
                email=email,
                nome_completo=f"Usuario Teste {role} {contador if contador > 1 else ''}".strip(),
                cpf=cpf_dinamico,
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
                # Gera uma matrícula aleatória (ex: 2026 + 4 números aleatórios)
                numero_aleatorio = random.randint(1000, 9999)
                user.matricula = f"2026{numero_aleatorio}"
                
            elif role in (CustomUser.Role.PROFESSOR, CustomUser.Role.SUPERVISOR):
                # Gera um CRP aleatório
                numero_crp = random.randint(10000, 99999)
                user.crp = f"{numero_crp}/RJ-{role}"
            
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