"""drf-spectacular OpenAPI extensions for the custom auth schemes (Story 11.9).

drf-spectacular cannot introspect ``OrgApiKeyAuthentication`` (a custom
``BaseAuthentication``) on its own, so this extension declares it as an
``apiKey`` security scheme in the generated schema. The module is imported from
``UsersConfig.ready`` so the extension registers at startup.
"""

from __future__ import annotations

from typing import Any

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class OrgApiKeyScheme(OpenApiAuthenticationExtension):  # type: ignore[no-untyped-call]
    """Describe ``OrgApiKeyAuthentication`` as an ``Api-Key`` header scheme.

    (drf-spectacular's ``__init_subclass__`` registration hook is untyped, hence
    the ignore above under mypy strict.)
    """

    target_class = "generate_sbom.users.authentication.OrgApiKeyAuthentication"
    name = "OrgApiKey"

    def get_security_definition(self, auto_schema: Any) -> dict[str, str]:
        """Return the OpenAPI security scheme for the Api-Key header auth."""
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Organization API key. Send as `Authorization: Api-Key <key>`.",
        }
