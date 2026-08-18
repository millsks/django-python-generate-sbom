"""Views shared across the project."""

from django.http import HttpRequest, JsonResponse


def health(request: HttpRequest) -> JsonResponse:
    """Unauthenticated liveness check used by the Docker Compose healthcheck.

    Deliberately does not touch the database so it reports healthy independent of
    migration/DB-boot timing; it exists only to gate ``depends_on`` ordering.
    """
    return JsonResponse({"status": "ok"})
