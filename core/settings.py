from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent


env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file)


def _normalize_async_database_url(url: str | None) -> str | None:
    if not url:
        return None
    scheme, sep, rest = url.partition("://")
    if not sep:
        return url
    clean_scheme = (
        scheme.replace("+asyncpg", "")
        .replace("+psycopg2", "")
        .replace("+psycopg", "")
    )
    return f"{clean_scheme}://{rest}"


environ.Env.DB_SCHEMES["postgresql+asyncpg"] = "django.db.backends.postgresql"

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-secret-key-change-me")

DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
TIME_ZONE = env("DJANGO_TIME_ZONE", default="Asia/Tehran")
ALLOWED_WS_ORIGINS = env.list("DJANGO_ALLOWED_WS_ORIGINS", default=[])

USE_PROXY_HEADERS = env.bool("DJANGO_USE_PROXY_HEADERS", default=True)

if USE_PROXY_HEADERS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=not DEBUG)
SESSION_COOKIE_SECURE = env.bool("DJANGO_SESSION_COOKIE_SECURE", default=not DEBUG)
CSRF_COOKIE_SECURE = env.bool("DJANGO_CSRF_COOKIE_SECURE", default=not DEBUG)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = env("DJANGO_SESSION_COOKIE_SAMESITE", default="Lax")
SECURE_REFERRER_POLICY = env("DJANGO_SECURE_REFERRER_POLICY", default="same-origin")
SECURE_HSTS_SECONDS = env.int(
    "DJANGO_SECURE_HSTS_SECONDS", default=0 if DEBUG else 3600
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG
)
SECURE_HSTS_PRELOAD = env.bool("DJANGO_SECURE_HSTS_PRELOAD", default=False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = env("DJANGO_X_FRAME_OPTIONS", default="DENY")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'channels',
    'ai',
    'review',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'core.whitenoise.AsyncWhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'


database_url = env("DATABASE_URL", default=None, cast=str) or None

database_from_url = env.db("DATABASE_URL", default=database_url)
if database_from_url:
    DATABASES = {'default': database_from_url}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': env('POSTGRES_DB', default='okrcoach'),
            'USER': env('POSTGRES_USER', default='okrcoach'),
            'PASSWORD': env('POSTGRES_PASSWORD', default='okrcoach'),
            'HOST': env('POSTGRES_HOST', default='localhost'),
            'PORT': env('POSTGRES_PORT', default='5432'),
            'CONN_MAX_AGE': env.int('DJANGO_DB_CONN_MAX_AGE', default=60),
            'OPTIONS': {
                'sslmode': env.str('POSTGRES_SSL_MODE', default='prefer'),
            },
        }
    }

DATABASES['default']['ATOMIC_REQUESTS'] = env.bool(
    'DJANGO_DB_ATOMIC_REQUESTS', default=True
)

ASYNC_DATABASE_URL = env(
    "ASYNC_DATABASE_URL", default=database_url, cast=str
)
ASYNC_DATABASE_URL = _normalize_async_database_url(ASYNC_DATABASE_URL) or _normalize_async_database_url(database_url)
ASYNC_PG_POOL_MIN_SIZE = env.int("ASYNC_PG_POOL_MIN_SIZE", default=1)
ASYNC_PG_POOL_MAX_SIZE = env.int("ASYNC_PG_POOL_MAX_SIZE", default=5)

redis_url = env("REDIS_URL", default=None)
if redis_url:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [redis_url]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

OPENAI_API_KEY = env("OPENAI_API_KEY", default=None)
OPENAI_BASE_URL = env("OPENAI_BASE_URL", default=None)
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o-mini")
AI_TEMPERATURE = env.float("AI_TEMPERATURE", default=None)
AI_MAX_TOKENS = env.int("AI_MAX_TOKENS", default=None)
AI_REQUEST_TIMEOUT = env.int("AI_REQUEST_TIMEOUT", default=30)

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

LANGUAGE_CODE = 'en-us'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
WHITENOISE_USE_FINDERS = env.bool("WHITENOISE_USE_FINDERS", default=DEBUG)
WHITENOISE_AUTOREFRESH = env.bool("WHITENOISE_AUTOREFRESH", default=DEBUG)

MEDIA_URL = env("MEDIA_URL", default="/media/")
MEDIA_ROOT = BASE_DIR / "media"

AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default=None)
if AWS_STORAGE_BUCKET_NAME:
    STORAGES["default"] = {"BACKEND": "storages.backends.s3boto3.S3Boto3Storage"}
    AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default=None)
    AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default=None)
    AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default=None)
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)
    AWS_QUERYSTRING_AUTH = env.bool("AWS_QUERYSTRING_AUTH", default=False)
    AWS_S3_FILE_OVERWRITE = env.bool("AWS_S3_FILE_OVERWRITE", default=False)
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"
    elif AWS_S3_ENDPOINT_URL:
        MEDIA_URL = f"{AWS_S3_ENDPOINT_URL.rstrip('/')}/{AWS_STORAGE_BUCKET_NAME}/"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL", default=redis_url or "redis://localhost:6379/0"
)
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL
)
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = env.bool(
    "CELERY_TASK_EAGER_PROPAGATES", default=True
)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("DJANGO_LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {"level": env("DJANGO_LOG_LEVEL", default="INFO"), "handlers": ["console"], "propagate": False},
    },
}
