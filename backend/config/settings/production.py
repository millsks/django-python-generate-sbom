# Production settings.
#
# Object storage (django-storages / S3) is wired by the first artifact-persisting
# story (Epic 3).
from config.settings.base import *

DEBUG = False

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# JSON structured logs in production.
configure_structlog(json_logs=True)
