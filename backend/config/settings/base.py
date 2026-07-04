# Shared Django settings for the django-python-generate-sbom backend.
#
# All runtime configuration is read from environment variables via django-environ
# (NFR-5.2). Sensible non-secret defaults keep local dev and the test suite
# runnable without a populated .env. Object storage (django-storages / S3) is
# wired by the first story that persists artifacts (Epic 3); this module wires
# the database, Redis/Celery, and structured logging.
from pathlib import Path

import environ

from generate_sbom.common.logging import configure_structlog

# BASE_DIR is the backend/ directory (parent of config/).
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

SECRET_KEY = env.str("SECRET_KEY", default="django-insecure-dev-key-not-for-production")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_api_key",
    "generate_sbom.users",
    "generate_sbom.manifests",
]

AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    # Dual auth: programmatic (Api-Key) OR web UI (session). Views read the active
    # org via generate_sbom.users.auth.get_request_org (handles both paths).
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "generate_sbom.users.authentication.OrgApiKeyAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["generate_sbom.users.authentication.HasSessionOrApiKey"],
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Uploaded manifests / artifacts. Local dev + tests use the filesystem
# (FileSystemStorage → MEDIA_ROOT); production.py swaps the default to S3/MinIO
# via django-storages (AD-6). Storage paths are org-scoped (NFR-1.2).
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Non-manifest: Vite already content-hashes SPA assets, so Django's manifest
    # hashing would rewrite names the built index.html doesn't reference.
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Built React SPA (frontend/dist/ at the project root, AD-5). Included only when
# present so `check` / collectstatic don't warn before the frontend is built.
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
STATICFILES_DIRS = [FRONTEND_DIST] if FRONTEND_DIST.exists() else []
SPA_INDEX_FILE = FRONTEND_DIST / "index.html"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Redis / Celery (AD-4, AD-6) ---
REDIS_URL = env.str("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_DEFAULT_QUEUE = "pipeline"
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_TASK_SOFT_TIME_LIMIT", default=1800)
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=2100)

# Per-org concurrency gate limit (AD-7 / NFR-4.1); consumed by Epic 3.
SBOM_MAX_CONCURRENT_JOBS_PER_ORG = env.int("SBOM_MAX_CONCURRENT_JOBS_PER_ORG", default=5)

# --- Structured logging (NFR-5.3) ---
# JSON by default (production); local.py overrides to the console renderer.
LOG_JSON = env.bool("LOG_JSON", default=True)
configure_structlog(json_logs=LOG_JSON)
