- Builda e sobe o container
docker compose up -d --build 
- faz as migrations
docker compose exec django-web python3 manage.py makemigrations core 
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