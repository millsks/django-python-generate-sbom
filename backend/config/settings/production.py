# Production settings.
#
# Story 1.3 hardens this further (django-environ, S3 storage, structlog JSON).
from config.settings.base import *

DEBUG = False

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
