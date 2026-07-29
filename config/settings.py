import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

from dotenv import load_dotenv


<<<<<<< HEAD
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-key")

=======
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

>>>>>>> 93ecbb2a66600214ce4ba76be4ff0cb02a1db06a
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
<<<<<<< HEAD
    ALLOWED_HOSTS = ["localhost", "127.0.0.1",'host.docker.internal']
=======
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
>>>>>>> 93ecbb2a66600214ce4ba76be4ff0cb02a1db06a


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
    "professors",
    "students",
    "supervisor",
    "administration",
    "superadmin",
    "localflavor",
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

# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

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

AUTH_USER_MODEL = "core.CustomUser"
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'lista_tarefas'