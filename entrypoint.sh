#!/bin/sh

# Sai imediatamente se algum comando falhar
set -e

echo "⏳ Aplicando migrações do banco de dados..."
python3 manage.py makemigrations core
python3 manage.py migrate

# Aqui está o "if" que você queria!
if [ "$NODE_ENV" = "dev" ]; then
    echo "🛠️ Ambiente de Desenvolvimento detectado. Populando o banco..."
    # Roda o seu comando customizado apenas no DEV
    python3 manage.py popular_users
    python3 manage.py popular_users
    python3 manage.py popular_users
else
    echo "🚀 Ambiente de Produção detectado. Pulando a geração de usuários de teste."
fi

echo "🟢 Iniciando o servidor Gunicorn..."
# O comando 'exec' faz o Gunicorn assumir o processo principal (PID 1) do contêiner
exec gunicorn --bind 0.0.0.0:8000 --workers 3 config.wsgi:application