# Refs: https://www.docker.com/blog/how-to-dockerize-django-app/ 
#Nao sei qual versão de python estamos usando então coloquei a que usei no momento e usei a versao slim para pesar menos
FROM python:3.14.5-slim

#Cria e seta a pasta app como workdir
WORKDIR /app

#Cancela a criacao de arquivos pycache
ENV PYTHONDONTWRITEBYTECODE = 1
#Previne o python de "demorar" a entregar as mensagens(prints)
ENV PYTHONUNBUFFERED = 1

# Atualiza o apt(pip do linux), instala os compiladores base, remove o cache criado durante as instalações
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]