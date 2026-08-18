"""Every refusal from the users API answers in the documented envelope (Story 22.12).

The audit found ~25 uncovered lines in `users/views.py`, and all of them were refusals:
`_validation_error`, the `_NOT_ADMIN` 403s, the 404s, and the `MembershipError` 400s. The
happy paths were well covered; nothing exercised what a caller sees when something is wrong.

That matters more here than coverage arithmetic, because these endpoints are consumed by
code, not people. Each `@extend_schema` promises `ErrorResponseSerializer` — an object with
`error` and `code` — and a client branching on `code` breaks silently if a path returns a bare
DRF `{"detail": ...}` or a 500 instead. So the contract is asserted as one sweep across the
surface rather than endpoint by endpoint.

**A note on the 403s.** `get_admin_org` has returned the same value as `get_request_org` since
Story 21.24 removed authentication, so `_NOT_ADMIN` ("Admin privileges are required") is now
reachable only when *no organization exists at all* — the caller is not being refused for lack
of privilege. The message is stale, and these tests pin the shape and status rather than
endorse the wording; see the test at the bottom, which names it. Epics 17-18 restore a real
authorization decision at that seam, at which point the message becomes true again.
"""

from __future__ import annotations

import pytest
from django.test import Client

from inventory.users.models import Org, OrgApiKey, OrgMembership
from inventory.users.services import create_org, register_user

pytestmark = pytest.mark.django_db

PASSWORD = "pw12345678"


@pytest.fixture
def org(db: None) -> Org:
    """A workspace to act in, so refusals are about the request rather than a missing org."""
    return create_org(name="Envelope Test", admin_user=None)


def _assert_envelope(response: object, expected_status: int, expected_code: str | None = None) -> None:
    """Assert the response is the documented `{error, code}` object at the given status."""
    status_code = response.status_code  # type: ignore[attr-defined]
    body = response.json()  # type: ignore[attr-defined]
    assert status_code == expected_status, f"got {status_code}: {body}"
    assert isinstance(body, dict), body
    assert set(body) >= {"error", "code"}, f"not the documented envelope: {body}"
    assert body["error"], "the envelope must carry a human-readable message"
    if expected_code is not None:
        assert body["code"] == expected_code, body


# --- Bad payloads -----------------------------------------------------------------------------

# (path, payload) pairs whose serializer must reject the body.
INVALID_PAYLOADS = [
    ("/api/v1/orgs/create/", {"name": ""}),
    ("/api/v1/orgs/members/", {"email": "not-an-email"}),
    ("/api/v1/orgs/members/create-user/", {"email": "nope", "temp_password": "x"}),
    ("/api/v1/orgs/promote-admin/", {"user_id": "not-a-number"}),
    ("/api/v1/orgs/demote-admin/", {}),
    ("/api/v1/keys/", {"name": ""}),
    ("/api/v1/admin/global-admins/", {"email": "not-an-email"}),
]


@pytest.mark.parametrize(("path", "payload"), INVALID_PAYLOADS)
def test_an_invalid_payload_returns_the_validation_envelope(path: str, payload: dict, org: Org) -> None:
    """400 with `code: validation_error`, and the serializer's own message.

    The message is passed through rather than replaced, so a client can show which field was
    wrong; `_validation_error` takes the first error, which is why the code is what clients
    should branch on.
    """
    response = Client().post(path, payload, content_type="application/json")

    _assert_envelope(response, 400, "validation_error")


# --- Things that do not exist ------------------------------------------------------------------


def test_removing_an_unknown_member_is_a_404_envelope(org: Org) -> None:
    response = Client().delete("/api/v1/orgs/members/999999/")

    _assert_envelope(response, 404, "not_a_member")


def test_promoting_an_unknown_user_is_a_404_envelope(org: Org) -> None:
    response = Client().post("/api/v1/orgs/promote-admin/", {"user_id": 999999}, content_type="application/json")

    _assert_envelope(response, 404, "not_a_member")


def test_demoting_an_unknown_user_is_a_404_envelope(org: Org) -> None:
    response = Client().post("/api/v1/orgs/demote-admin/", {"user_id": 999999}, content_type="application/json")

    _assert_envelope(response, 404, "not_a_member")


def test_revoking_an_unknown_key_is_a_404_envelope(org: Org) -> None:
    response = Client().delete("/api/v1/keys/00000000-0000-0000-0000-000000000000/")

    _assert_envelope(response, 404, "not_found")


def test_revoking_a_global_admin_who_does_not_exist_is_a_404_envelope(org: Org) -> None:
    response = Client().delete("/api/v1/admin/global-admins/999999/")

    _assert_envelope(response, 404, "not_found")


def test_a_key_belonging_to_another_org_is_not_found_rather_than_forbidden(org: Org) -> None:
    """Cross-org lookups must not disclose that the row exists (AD-2).

    `revoke_api_key` scopes by org, so the answer is the same 404 an absent key gets — which
    is the point: a 403 here would confirm the key's existence to another tenant.
    """
    other = create_org(name="Other Tenant", admin_user=None)
    response = Client().post("/api/v1/keys/", {"name": "theirs"}, content_type="application/json")
    key_id = response.json()["id"]
    OrgApiKey.objects.filter(pk=key_id).update(org=other)

    _assert_envelope(Client().delete(f"/api/v1/keys/{key_id}/"), 404, "not_found")


# --- Domain refusals ----------------------------------------------------------------------------


def test_adding_a_member_who_is_not_registered_returns_the_domain_code(org: Org) -> None:
    """`MembershipError` codes reach the client unchanged, not flattened to a generic 400."""
    response = Client().post(
        "/api/v1/orgs/members/", {"email": "stranger@example.com"}, content_type="application/json"
    )

    _assert_envelope(response, 400)
    assert response.json()["code"] != "validation_error", "a domain refusal should carry its own code"


def test_creating_a_member_user_with_a_taken_email_returns_email_taken(org: Org) -> None:
    register_user(email="taken@example.com", password=PASSWORD)

    response = Client().post(
        "/api/v1/orgs/members/create-user/",
        {"email": "taken@example.com", "temp_password": PASSWORD},
        content_type="application/json",
    )

    _assert_envelope(response, 400, "email_taken")


def test_demoting_the_last_admin_is_refused_with_its_own_code(org: Org) -> None:
    """The guard that protects an org from losing every admin (Story 2.20)."""
    user = register_user(email="solo@example.com", password=PASSWORD)
    OrgMembership.objects.create(org=org, user=user, role=OrgMembership.Role.ADMIN)

    response = Client().post("/api/v1/orgs/demote-admin/", {"user_id": user.pk}, content_type="application/json")

    _assert_envelope(response, 400)
    assert response.json()["code"] != "validation_error"


def test_switching_to_an_org_the_caller_cannot_reach_is_a_403_envelope(org: Org) -> None:
    response = Client().post("/api/v1/orgs/switch/", {"slug": "no-such-org"}, content_type="application/json")

    _assert_envelope(response, 403, "not_a_member")


# --- The org-scoped endpoints when there is no org -----------------------------------------------

ORG_SCOPED_WRITES = [
    ("post", "/api/v1/orgs/members/", {"email": "someone@example.com"}),
    ("post", "/api/v1/orgs/members/create-user/", {"email": "new@example.com", "temp_password": PASSWORD}),
    ("post", "/api/v1/orgs/promote-admin/", {"user_id": 1}),
    ("post", "/api/v1/orgs/demote-admin/", {"user_id": 1}),
    ("post", "/api/v1/keys/", {"name": "k"}),
    ("delete", "/api/v1/orgs/members/1/", None),
    ("delete", "/api/v1/keys/abc/", None),
    ("post", "/api/v1/orgs/leave/", None),
    ("get", "/api/v1/orgs/members/", None),
]


@pytest.mark.parametrize(("method", "path", "payload"), ORG_SCOPED_WRITES)
def test_org_scoped_endpoints_refuse_cleanly_when_no_org_exists(
    method: str, path: str, payload: dict | None, no_organizations: None
) -> None:
    """A 4xx envelope, never a 500 and never an unhandled `None` org."""
    client = Client()
    if method == "get":
        response = client.get(path)
    elif method == "delete":
        response = client.delete(path)
    else:
        response = client.post(path, payload, content_type="application/json")

    assert 400 <= response.status_code < 500, f"{path} returned {response.status_code}"
    _assert_envelope(response, response.status_code)


def test_the_no_org_403_still_claims_to_be_about_admin_privileges(no_organizations: None) -> None:
    """Pins the stale message so a future change to it is a deliberate edit, not a surprise.

    `get_admin_org` is `get_request_org` since Story 21.24, so this 403 fires when the database
    has no organization — not because the caller lacks privilege. The wording is left alone
    because Epics 17-18 restore a real admin decision at this exact seam and make it true
    again; this test exists so that whoever changes it sees why it reads the way it does.
    """
    response = Client().post("/api/v1/keys/", {"name": "k"}, content_type="application/json")

    assert response.status_code == 403
    assert response.json()["code"] == "not_admin"


# --- Codes the app no longer returns --------------------------------------------------------

RETIRED_CODES = ["not_global_admin", "invalid_credentials"]


@pytest.mark.parametrize("code", RETIRED_CODES)
def test_a_retired_error_code_appears_nowhere_in_the_source(code: str) -> None:
    """`not_global_admin` and `invalid_credentials` are gone; keeping them was worse than dead code.

    Both were left behind as module constants after Stories 21.24 and 22.8 removed the login
    and the global-admin gate — `_NOT_GLOBAL_ADMIN` was even commented as "retained for the
    schema", which no `@extend_schema` referenced. Coverage cannot catch this: a module-level
    assignment always executes, so `users/views.py` read 100% while advertising a refusal the
    app cannot make.

    That is the same failure as the deleted `get_org_scoped_object_or_404` — a security-shaped
    name that enforces nothing, and that the next reader would reasonably believe.
    """
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "src"
    offenders = [str(path.relative_to(src)) for path in src.rglob("*.py") if code in path.read_text(encoding="utf-8")]

    assert not offenders, f"'{code}' is no longer returned by anything but still appears in {offenders}"


@pytest.mark.parametrize("code", RETIRED_CODES)
def test_the_api_reference_does_not_promise_a_retired_code(code: str) -> None:
    """The docs claimed 403 `not_global_admin` on endpoints that cannot return it.

    Documenting protection the app does not have is worse than documenting nothing: a reader
    concludes the endpoint is gated. The two mentions that remain are explicit statements that
    the code was retired, which is why they are matched on rather than banned outright.
    """
    from pathlib import Path

    docs = Path(__file__).resolve().parents[2] / "docs" / "api"
    for page in docs.glob("*.md"):
        for number, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
            if code not in line:
                continue
            assert any(word in line.lower() for word in ("not returned", "removed", "retired", "no longer")), (
                f"{page.name}:{number} mentions `{code}` without saying it is retired: {line.strip()}"
            )
