- Builda e sobe o container
docker compose up -d --build 
- faz as migrations
docker compose exec django-web python3 manage.py makemigrations core areas teacher students patient screening documents 
- migra a tabela
docker compose exec django-web python3 manage.py migrate 
- faz os usuarios em todas as roles
docker compose exec django-web python3 manage.py popular_users 
- faz usuario por role
docker compose exec django-web python3 manage.py popular_users --roles AL PR 
- derruba docker
docker compose down -v 
- Comando para criar um superuser
docker compose exec django-web python3 manage.py createsuperuser - cria superuser


- [x] So podera execuutar se a env for tipo dev
- [] Adicionar comandos no dockerfile

## Telas do Professor

Deixa a área do Professor pronta para testar: pacientes que a coordenação já
encaminhou, alunos orientados para receber o caso e prontuários com evolução.
Depende do `populate_users` (precisa de pelo menos uma área de atuação; o
Coordenador é opcional e entra como quem encaminhou e quem confirmou evolução).

```bash
docker exec django-docker python manage.py populate_users
docker exec django-docker python manage.py populate_teacher_home
```

Pode rodar de novo quantas vezes quiser: o comando refaz as triagens, os
encaminhamentos e as evoluções dos mesmos pacientes de demonstração.

| Conta | Senha | Para quê |
|---|---|---|
| `professor.demo@teste.com` | `Professor@123` | O professor que recebe o encaminhamento |
| `aluno.prof1@teste.com` … `aluno.prof3@teste.com` | `Professor@123` | Os alunos orientados que aparecem na caixa de alocação |

### Comportamento esperado

| Tela | O que deve aparecer |
|---|---|
| Encaminhar | Três pacientes na fila "aguardando encaminhamento" (José Santos, Camila Duarte e Rafael Nunes), os três alunos em "Alocar para aluno(s) orientado(s)" e dois casos em "Encaminhamentos recentes" |
| Prontuários e evolução | Seis evoluções, três de cada paciente em atendimento (Lucas Prado com a Marina Costa, Bianca Moraes com o Pedro Alves), a mais antiga de cada um já confirmada pelo Coordenador |
| Página inicial | "Avaliações pendentes" com as quatro evoluções sem confirmação, que são também as atividades recentes |
| Presença e Avaliações | Marina Costa e Pedro Alves; o João Ribeiro não aparece porque essas telas só mostram aluno com caso aberto na área do orientador |