import os
from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "host.docker.internal"]

if not SECRET_KEY:
    SECRET_KEY = "django-insecure-development-only-key"

# Lê as credenciais e o backend do arquivo .env
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in ("true", "1", "t")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", "nao-responda@seusistema.com.br"
)