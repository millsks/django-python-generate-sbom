# Production settings.
#
# Object storage (django-storages / S3) is wired by the first artifact-persisting
# story (Epic 3).
from config.settings.base import *

DEBUG = False

# API docs are off by default in production (Story 11.9); set API_DOCS_ENABLED=true to
# expose /api/schema/, /api/docs/, and /api/redoc/ on a deployed instance.
API_DOCS_ENABLED = env.bool("API_DOCS_ENABLED", default=False)

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# JSON structured logs in production.
configure_structlog(json_logs=True)

# Shared Redis-backed external-API cache across analysis workers (FR-5.5).
REQUESTS_CACHE_BACKEND = "redis"

# Object storage: manifests/artifacts go to S3/MinIO via django-storages (AD-6).
AWS_STORAGE_BUCKET_NAME = env.str("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_ENDPOINT_URL = env.str("AWS_S3_ENDPOINT_URL", default="")
# Browser-reachable endpoint for presigned download URLs (AD-11). The internal
# AWS_S3_ENDPOINT_URL (e.g. http://minio:9000) isn't resolvable from a user's
# browser; set this to the host-published endpoint (e.g. http://localhost:9000).
AWS_S3_PUBLIC_ENDPOINT_URL = env.str("AWS_S3_PUBLIC_ENDPOINT_URL", default="")
AWS_ACCESS_KEY_ID = env.str("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env.str("AWS_SECRET_ACCESS_KEY", default="")
AWS_S3_FILE_OVERWRITE = False

STORAGES = {
    # django-storages 1.14: the S3 backend class is `S3Storage` in
    # `storages.backends.s3`. We subclass it to serve presigned URLs via a
    # browser-reachable public endpoint (the legacy `S3Boto3Storage` lives in `.s3boto3`).
    "default": {"BACKEND": "generate_sbom.common.storage.PublicEndpointS3Storage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
