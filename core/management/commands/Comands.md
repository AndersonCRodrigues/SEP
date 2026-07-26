docker compose up -d --build - Builda e sobe o container

docker compose exec django-web python3 manage.py makemigrations core - faz as migrations

docker compose exec django-web python3 manage.py migrate - migra a tabela

docker compose exec django-web python3 manage.py TestUsers - faz os usuarios em todas as ro

docker compose exec django-web python3 manage.py TestUsers --roles AL PR - faz usuario ppor role

docker compose down -v - derruba docker

docker compose exec django-web python3 manage.py createsuperuser - cria super user