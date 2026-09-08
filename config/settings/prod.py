from .base import DEBUG, SECRET_KEY, ALLOWED_HOSTS
import os
from django.core.exceptions import ImproperlyConfigured

DEBUG = False

if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY não encontrada! Configure a variável no ambiente de produção.")

_allowed_hosts_env = os.getenv("DJANGO_ALLOWED_HOSTS", "")
if _allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in _allowed_hosts_env.split(",") if host.strip()]
else:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS deve estar configurado em produção.")

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = f"Sistema <{EMAIL_HOST_USER}>"