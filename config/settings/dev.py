from .base import *

#Checar como relacionar o NODE_ENV com o debug
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
#Devo encontrar uma chave base para a dev ou mantem assim pois a env da prod sera diferente?
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
#Perguntar para o thiago para que isso
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
#Quais serao os allowed hosts de cada um?
ALLOWED_HOSTS = ["localhost", "127.0.0.1",'host.docker.internal']

#E a database? o prod tambem usara docker? se sim devo criar mais um container semelhante para a dev?
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

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'nao-responda@seusistema.com.br'