import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-key")

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = os.getenv(
            "DJANGO_SECRET_KEY", "django-insecure-development-only-key"
        )
    else:
        raise RuntimeError(
            "DJANGO_SECRET_KEY must be set when DEBUG=False. "
            "Configure it using environment variables."
        )


_allowed_hosts_env = os.getenv("DJANGO_ALLOWED_HOSTS", "")

if _allowed_hosts_env:
    ALLOWED_HOSTS = [
        host.strip() for host in _allowed_hosts_env.split(",") if host.strip()
    ]
else:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1",'host.docker.internal']


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "core",
    "patients",
    "screening",
    'localflavor'
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
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
        "DIRS": [BASE_DIR/'templates'],
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

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.MinimumLengthValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.CommonPasswordValidator"),
    },
    {
        "NAME": ("django.contrib.auth.password_validation.NumericPasswordValidator"),
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True




STATIC_URL = "static/"

DB_ENGINE = os.getenv("DATABASE_ENGINE", "postgresql")


DATABASES = {
    "default": {
        "ENGINE": f"django.db.backends.{DB_ENGINE}",
        "NAME": os.getenv("DATABASE_NAME", "django_db"),
        "USER": os.getenv("DATABASE_USERNAME", "myprojectuser"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", "password"),
        "HOST": os.getenv("DATABASE_HOST", "127.0.0.1"),
        "PORT": os.getenv("DATABASE_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "core.CustomUser"
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'lista_tarefas'