# Refs: https://www.docker.com/blog/how-to-dockerize-django-app/ 
#Nao sei qual versão de python estamos usando então coloquei a que usei no momento e usei a versao slim para pesar menos
#Estágio de Construção
FROM python:3.12-slim AS builder

#Cria e seta a pasta app como workdir
WORKDIR /app

#Cancela a criacao de arquivos pycache
ENV PYTHONDONTWRITEBYTECODE=1
#Previne o python de "demorar" a entregar as mensagens(prints)
ENV PYTHONUNBUFFERED=1

# Atualiza o apt(pip do linux), instala os compiladores base, remove o cache criado durante as instalações
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia o requirements, atualiza o pip e instala o requirements
COPY requirements.txt /app/

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

#Estagio de produção
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Intala apenas a biblioteca de execução do PostgreSQL
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*
# Cria o uusu;ario não-root
RUN useradd -m -r appuser

WORKDIR /app

# Copia as libs (libraries) Python já instaladas do estágio "builder" sem fixar a versão minor.
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/
# Copia o código da sua aplicação já atribuindo as permissões ao usuuário appuser
COPY --chown=appuser:appuser . .
#Troca para o user
USER appuser

EXPOSE 8000

CMD ["sh", "-c", "python3 manage.py makemigrations core && python3 manage.py makemigrations areas && python3 manage.py makemigrations students && python3 manage.py makemigrations teacher && python3 manage.py migrate && python3 manage.py popular_users && python3 manage.py setup_roles && gunicorn --bind 0.0.0.0:8000 --workers 3 config.wsgi:application"]