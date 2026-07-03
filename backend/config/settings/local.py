# Local development settings.
from config.settings.base import *

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Human-friendly console logs in local dev (base configured JSON).
configure_structlog(json_logs=False)
