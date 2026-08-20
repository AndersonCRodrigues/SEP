#!/bin/sh

# Sai imediatamente se algum comando falhar
set -e

echo "⏳ Verificando e aplicando migrações..."
python3 manage.py makemigrations core areas teacher students patient documents audit triage
python3 manage.py migrate

# Executa a criação de dados apenas se for ambiente de desenvolvimento
if [ "$NODE_ENV" = "dev" ]; then
    echo "🛠️ Ambiente de Desenvolvimento detectado. Populando banco e configurando roles..."
    python3 manage.py populate_users --qtd 3
    python3 manage.py setup_roles
else
    echo "🚀 Ambiente de Produção detectado. Pulando comandos de setup iniciais."
fi

echo "🟢 Iniciando o servidor Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --workers 3 config.wsgi:application