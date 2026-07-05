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
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "generate_sbom.users",
    "generate_sbom.manifests",
    "generate_sbom.sbom",
    "generate_sbom.analysis",
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
    # OpenAPI schema generation for the interactive docs (Story 11.9, drf-spectacular).
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# OpenAPI / Swagger UI (Story 11.9). Assets are self-hosted via drf-spectacular-sidecar
# (SIDECAR) so the docs work without any external CDN. API_DOCS_ENABLED gates whether the
# /api/schema/, /api/docs/, and /api/redoc/ endpoints are served — on in development, and
# overridable per environment (production defaults it off; see settings/production.py).
API_DOCS_ENABLED = env.bool("API_DOCS_ENABLED", default=True)

SPECTACULAR_SETTINGS = {
    "TITLE": "generate-sbom API",
    "DESCRIPTION": "REST API for uploading manifests, running SBOM jobs, and reading "
    "vulnerability, license, dependency-graph, and version-currency reports.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Public serve permissions so the docs are reachable without a session/API key;
    # exposure itself is gated by API_DOCS_ENABLED at the URLconf level.
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    # Self-hosted UI assets (no external CDN).
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
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

# External-API HTTP cache backend for the analysis subsystem (requests-cache).
# "memory" is per-process and network-free (tests/local); production uses "redis"
# so the cache is shared across analysis workers (FR-5.5).
REQUESTS_CACHE_BACKEND = env.str("REQUESTS_CACHE_BACKEND", default="memory")
CELERY_TASK_DEFAULT_QUEUE = "pipeline"
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_TASK_SOFT_TIME_LIMIT", default=1800)
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=2100)

# Per-org concurrency gate limit (AD-7 / NFR-4.1); consumed by Epic 3.
SBOM_MAX_CONCURRENT_JOBS_PER_ORG = env.int("SBOM_MAX_CONCURRENT_JOBS_PER_ORG", default=5)

# Version-currency LTS registry (FR-5.4): a JSON file path OR inline JSON mapping
# package name → LTS version string. Extends/overrides the built-in defaults.
SBOM_LTS_REGISTRY = env.str("SBOM_LTS_REGISTRY", default="")

# parselmouth conda↔PyPI name mapping source (Story 8.10), refreshed by a beat task.
PARSELMOUTH_MAPPING_URL = env.str(
    "PARSELMOUTH_MAPPING_URL",
    default="https://raw.githubusercontent.com/prefix-dev/parselmouth/main/files/compressed_mapping.json",
)

# --- Structured logging (NFR-5.3) ---
# JSON by default (production); local.py overrides to the console renderer.
LOG_JSON = env.bool("LOG_JSON", default=True)
configure_structlog(json_logs=LOG_JSON)
