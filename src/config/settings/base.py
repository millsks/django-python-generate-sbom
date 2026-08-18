# Shared Django settings for the django-python-generate-sbom backend.
#
# All runtime configuration is read from environment variables via django-environ
# (NFR-5.2). Sensible non-secret defaults keep local dev and the test suite
# runnable without a populated .env. Object storage (django-storages / S3) is
# wired by the first story that persists artifacts (Epic 3); this module wires
# the database, Redis/Celery, and structured logging.
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _package_version
from pathlib import Path

import environ

# The redundant alias is deliberate: local.py and production.py reach this name through
# `from config.settings.base import *`, and mypy's strict `no_implicit_reexport` does not
# re-export a plain import. `X as X` marks it an explicit re-export, which keeps the alias
# here — the one place that already imports from the app — instead of adding a second
# config -> app import in each settings module. (`pixi run check` only started covering
# src/config/ in Story 21.1, which is why this was never flagged before.)
from inventory.common.logging import configure_structlog as configure_structlog

# BASE_DIR is the REPOSITORY ROOT. Four `parent` hops from this file:
# src/config/settings/base.py -> settings -> config -> src -> <repo root>.
# Story 21.1 added the fourth hop when the tree moved from backend/ to src/;
# an off-by-one here silently relocates the SQLite DB, media/, and staticfiles/
# instead of raising, so tests/unit/test_settings_paths.py asserts it.
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

# APPS_DIR is the host project package — the home of project-wide templates,
# static assets, and the concrete `User` model (reference layout; Story 21.2).
APPS_DIR = BASE_DIR / "src" / "django_service"

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
    # Celery result backend for the containerless local dev path (Story 20.4): stores
    # task results in the (SQLite) DB via `django-db` so local dev needs no Redis. The
    # container/prod path keeps the Redis result backend (CELERY_RESULT_BACKEND below).
    "django_celery_results",
    # --- Server-rendered UI stack (Story 21.3) ---
    # crispy_forms renders forms as Bootstrap markup; crispy_bootstrap5 is the pack it
    # needs (crispy ships none of its own). django_tables2 + django_filters give
    # server-rendered sortable/paginated/filterable tables.
    "crispy_forms",
    "crispy_bootstrap5",
    "django_tables2",
    "django_filters",
    # Host project: owns the concrete User under the `users` label (Story 21.2).
    # Listed BEFORE the app so the swappable user model is registered first.
    "django_service.users",
    # The one reusable app, imported unqualified from the src/django_apps path root.
    # Replaces the former four labels (users/manifests/sbom/analysis), which are now
    # plain subpackages of `inventory` rather than separate Django apps.
    "inventory",
]

# UNCHANGED as a string, deliberately: dissolving the old `users` app freed the label and
# django_service.users re-took it, so there is no swappable-model migration to reconcile
# and no third-party migration referencing this setting has to change (Story 21.2).
AUTH_USER_MODEL = "users.User"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    # Dual auth: programmatic (Api-Key) OR web UI (session). Views read the active
    # org via inventory.users.auth.get_request_org (handles both paths).
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "inventory.users.authentication.OrgApiKeyAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["inventory.users.authentication.HasSessionOrApiKey"],
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
    "vulnerability, license, and version-currency reports.",
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

# TWO template roots, deliberately (Story 21.3):
#   DIRS      -> the project SHELL (base.html + error pages). Host chrome, owned by
#                django_service.
#   APP_DIRS  -> page templates under src/django_apps/inventory/templates/inventory/.
# Keeping them apart is what lets the app's templates travel to another host later; it
# costs nothing now.
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [APPS_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Product name (two forms) + role-gated navigation state, so no template
                # hardcodes either string or recomputes the role gates (Story 21.3).
                "django_service.context_processors.ui",
            ],
            # Registered explicitly because `django_service` is the host PACKAGE, not an
            # installed app — Django only auto-discovers templatetags/ from INSTALLED_APPS.
            # Adding the package as an app purely to expose one tag would also pull its
            # templates and static in through APP_DIRS, which the explicit DIRS and
            # STATICFILES_DIRS already handle (Story 21.18).
            "libraries": {"ui_icons": "django_service.templatetags.ui_icons"},
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
# BASE_DIR is now the repo root itself (Story 21.1), so no `.parent` hop here.
# Project-wide static: the vendored Bootstrap/htmx assets and the icon sprite live under
# django_service (Story 21.3). App static resolves separately through
# AppDirectoriesFinder at src/django_apps/inventory/static/inventory/.
STATICFILES_DIRS = [APPS_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Authentication redirects (Story 21.4) ---
# Django defaults LOGIN_URL to /accounts/login/, which this project has never served. The
# access-control mixins send anonymous users here (with `next`), so it has to be right.
# Story 21.5 replaces the SPA's /login with the server-rendered page at the same path.
LOGIN_URL = "/login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# --- Server-rendered UI configuration (Story 21.3) ---
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"
# django-tables2 defaults to its own plain template; point it at the Bootstrap 5 one so
# every table rendered from 21.10 onward matches the rest of the UI without per-table config.
DJANGO_TABLES2_TEMPLATE = "django_tables2/bootstrap5.html"

# --- Product name: defined ONCE, in two forms (Story 21.3, AC #4) ---
# Carries over the rule Story 12.6 established for the SPA's APP_NAME: the name is a
# single source, never a literal in a template. Two forms because the header brand and a
# per-page <title> suffix want the short one while documents and the landing page want
# the full one. Exposed to templates by django_service.context_processors.ui.
PRODUCT_NAME = "Python Inventory Supply Lens"
PRODUCT_NAME_SHORT = "Supply Lens"

# Footer + header chrome values, mirroring the SPA's config.ts so the server-rendered
# shell reproduces it (Story 12.3 footer, Story 11.8 header links, Story 11.20 API docs
# link). Env-overridable exactly as the Vite VITE_* equivalents were.
# Read from the installed distribution rather than hardcoded: the SPA footer mirrored
# package.json, and Story 21.19 deletes that. Still env-overridable so a deployment can pin a
# display version without a rebuild, matching the old VITE_* behaviour.
try:
    _DISTRIBUTION_VERSION = _package_version("generate-sbom")
except PackageNotFoundError:  # pragma: no cover - only when running from a bare checkout
    _DISTRIBUTION_VERSION = "0.0.0"
PRODUCT_VERSION = env.str("PRODUCT_VERSION", default=_DISTRIBUTION_VERSION)
REPO_URL = env.str("REPO_URL", default="https://github.com/millsks/django-python-generate-sbom")
DOCS_URL = env.str("DOCS_URL", default="https://millsks.github.io/django-python-generate-sbom/")

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

# Artifact retention window in days (Story 7.1): how long a job's SBOM + analysis-report
# blobs are kept before the daily cleanup purges them. Job metadata is retained forever.
# Defaults to 30 days; override via the ARTIFACT_RETENTION_DAYS env var.
ARTIFACT_RETENTION_DAYS = env.int("ARTIFACT_RETENTION_DAYS", default=30)

# Version-currency LTS registry (FR-5.4): a JSON file path OR inline JSON mapping
# package name → LTS version string. Extends/overrides the built-in defaults.
SBOM_LTS_REGISTRY = env.str("SBOM_LTS_REGISTRY", default="")

# parselmouth conda↔PyPI name mapping source (Story 8.10), refreshed by a beat task.
PARSELMOUTH_MAPPING_URL = env.str(
    "PARSELMOUTH_MAPPING_URL",
    default="https://raw.githubusercontent.com/prefix-dev/parselmouth/main/files/compressed_mapping.json",
)
# Authoritative per-package PyPI→conda lookup (Story 8.24), used only to disambiguate the
# ~1.5% of PyPI names with multiple conda candidates. `<base>/<normalized-name>.json`.
# Set empty to disable the per-package network call (falls back to the bulk map).
PARSELMOUTH_PYPI_TO_CONDA_URL = env.str(
    "PARSELMOUTH_PYPI_TO_CONDA_URL",
    default="https://conda-mapping.prefix.dev/pypi-to-conda-v1/conda-forge/",
)

# --- Structured logging (NFR-5.3) ---
# JSON by default (production); local.py overrides to the console renderer.
LOG_JSON = env.bool("LOG_JSON", default=True)
configure_structlog(json_logs=LOG_JSON)
