from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "host.docker.internal"]

if not SECRET_KEY:
    # Chave de desenvolvimento: prod.py levanta erro quando ela falta.
    SECRET_KEY = "django-insecure-development-only-key"  # nosec B105

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "nao-responda@seusistema.com.br"
