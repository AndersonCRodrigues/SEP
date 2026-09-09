import base64
import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from django.contrib.messages import constants as messages
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

FIELD_ENCRYPTION_KEY = os.environ.get("FIELD_ENCRYPTION_KEY")
if not FIELD_ENCRYPTION_KEY:
    raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY nao encontrada. Verifique o .env.")

try:
    if len(base64.urlsafe_b64decode(FIELD_ENCRYPTION_KEY)) != 32:
        raise ValueError
except Exception:
    raise ImproperlyConfigured(
        "FIELD_ENCRYPTION_KEY invalida: precisa ser 32 bytes em base64 url-safe. "
        'Gere com: python -c "from cryptography.fernet import Fernet; '
        'print(Fernet.generate_key().decode())"'
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "core",
    "patient",
    "teacher",
    "students",
    "supervisor",
    "administration",
    "superadmin",
    "localflavor",
    "areas",
    "triage",
    "documents",
    "audit.apps.AuditConfig",
    "crispy_forms",
    "crispy_bootstrap5",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "audit.middleware.AuditMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "core.cadastro.EmailOUMatricula",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

ENGINES_VALIDOS = {
    "django.db.backends.sqlite3",
    "django.db.backends.postgresql",
}

db_engine = os.getenv("DJANGO_DATABASE_ENGINE", "").strip()

if db_engine and db_engine not in ENGINES_VALIDOS:
    raise ImproperlyConfigured(
        f"DJANGO_DATABASE_ENGINE inválido: '{db_engine}'. "
        f"Valores aceitos: {', '.join(ENGINES_VALIDOS)}"
    )

if db_engine:
    db_name = os.getenv("DJANGO_DATABASE_NAME")
    db_user = os.getenv("DJANGO_DATABASE_USER")
    db_password = os.getenv("DJANGO_DATABASE_PASSWORD")
    db_host = os.getenv("DJANGO_DATABASE_HOST")
    db_port = os.getenv("DJANGO_DATABASE_PORT")

    missing_vars = [
        var_name
        for var_name, value in (
            ("DJANGO_DATABASE_NAME", db_name),
            ("DJANGO_DATABASE_USER", db_user),
            ("DJANGO_DATABASE_PASSWORD", db_password),
            ("DJANGO_DATABASE_HOST", db_host),
            ("DJANGO_DATABASE_PORT", db_port),
        )
        if not value
    ]

    if missing_vars:
        raise ImproperlyConfigured(
            "Bancos de dados configurados incorretamente: variável(is) de ambiente obrigatória(s) ausente(s): "
            + ", ".join(missing_vars)
        )

    DATABASES = {
        "default": {
            "ENGINE": db_engine,
            "NAME": db_name,
            "USER": db_user,
            "PASSWORD": db_password,
            "HOST": db_host,
            "PORT": db_port,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }



EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)



DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL","no-reply@sep.local")


if EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend":
    EMAIL_HOST = os.getenv("DJANGO_EMAIL_HOST")
    EMAIL_PORT = int(os.getenv("DJANGO_EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.getenv("DJANGO_EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.getenv("DJANGO_EMAIL_HOST_PASSWORD")
    EMAIL_USE_TLS = os.getenv("DJANGO_EMAIL_USE_TLS", "True").lower() == "true"



AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"

AUTH_USER_MODEL = "core.CustomUser"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home_redirect"

MESSAGE_TAGS = {
    messages.DEBUG: "secondary",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "danger",
    messages.ERROR: "danger",
}

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Republicacao explicita da API deste modulo (PEP 8 permite wildcard import
# quando o modulo de origem declara __all__). Isso evita que "import os",
# "Path", "base64" etc. vazem para dev.py/prod.py via `from .base import *`
# e restringe o wildcard só ao que é de fato uma Django setting.
__all__ = [
    "BASE_DIR",
    "SECRET_KEY",
    "FIELD_ENCRYPTION_KEY",
    "INSTALLED_APPS",
    "MIDDLEWARE",
    "AUTHENTICATION_BACKENDS",
    "ROOT_URLCONF",
    "TEMPLATES",
    "WSGI_APPLICATION",
    "DATABASES",
    "AUTH_PASSWORD_VALIDATORS",
    "LANGUAGE_CODE",
    "TIME_ZONE",
    "USE_I18N",
    "USE_TZ",
    "STATIC_URL",
    "AUTH_USER_MODEL",
    "LOGIN_URL",
    "LOGIN_REDIRECT_URL",
    "MESSAGE_TAGS",
    "CRISPY_ALLOWED_TEMPLATE_PACKS",
    "CRISPY_TEMPLATE_PACK",
]
