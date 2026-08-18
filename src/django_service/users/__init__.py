"""The host project's user identity app.

Owns the concrete ``User`` and nothing else. It keeps the app label ``users`` that
the dissolved ``generate_sbom.users`` app used to hold, so
``AUTH_USER_MODEL = "users.User"`` is unchanged (Story 21.2).
"""
