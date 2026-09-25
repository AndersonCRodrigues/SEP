import os

from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "host.docker.internal"]

if not SECRET_KEY:
    # Chave de desenvolvimento: prod.py levanta erro quando ela falta.
    SECRET_KEY = "django-insecure-development-only-key"  # nosec B105

# --- Estáticos em desenvolvimento (WhiteNoise) ---------------------------
# Em produção (base.py/prod.py) usamos CompressedManifestStaticFilesStorage,
# que exige rodar "collectstatic" a cada mudança para gerar um hash novo do
# arquivo. Como isso nunca roda automaticamente no dia a dia do dev, a tag
# {% static %} ficava presa no manifest antigo e só "atualizava" depois de
# um rebuild.
#
# Aqui trocamos para o storage simples (sem hash/manifest) e ligamos o modo
# de desenvolvimento do WhiteNoise: com WHITENOISE_USE_FINDERS ele serve os
# arquivos direto das pastas static (STATICFILES_DIRS / <app>/static) — as
# mesmas pastas que já estão montadas como volume no docker-compose — e com
# WHITENOISE_AUTOREFRESH ele reconfere o arquivo a cada request, então
# qualquer alteração aparece no próximo F5, sem precisar de collectstatic
# nem de reiniciar o container.
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

# Lê as credenciais e o backend do arquivo .env
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in ("true", "1", "t")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "nao-responda@seusistema.com.br")