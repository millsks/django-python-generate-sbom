"""Story 21.5: the server-rendered authentication pages.

The load-bearing tests here are the two that protect users rather than features: that a
failed login cannot be used to discover whether an account exists (AC #6), and that logging
out actually invalidates the session rather than merely redirecting.
"""

from __future__ import annotations

import re

import pytest
from django.contrib.auth import SESSION_KEY
from django.test import Client

from inventory.common.users import user_model
from inventory.users.forms import INVALID_CREDENTIALS
from inventory.users.models import OrgMembership
from inventory.users.services import register_user

LOGIN_URL = "/login"
REGISTER_URL = "/register"
LOGOUT_URL = "/logout"
PASSWORD = "corrects-horse-42"

# Two things legitimately differ between renders and must be masked before two responses
# can be compared for indistinguishability:
#   - the CSRF token, which is regenerated every render;
#   - the echoed email, because the form repopulates whatever the user typed. Echoing back
#     the submitted address discloses nothing — the submitter already knows it.
# Everything else must match, which is what makes the comparison meaningful.
CSRF_TOKEN = re.compile(r'value="[A-Za-z0-9]{32,}"')
EMAIL_VALUE = re.compile(r'value="[^"]*@[^"]*"')


def _body(response: object) -> str:
    html = response.content.decode()  # type: ignore[attr-defined]
    html = CSRF_TOKEN.sub('value="MASKED_TOKEN"', html)
    return EMAIL_VALUE.sub('value="MASKED_EMAIL"', html)


@pytest.fixture
def existing_user() -> None:
    register_user(email="user@example.com", password=PASSWORD)


# --- Rendering + ergonomics (AC #4) -----------------------------------------------------


@pytest.mark.django_db
def test_login_page_renders_with_the_email_field_autofocused() -> None:
    html = Client().get(LOGIN_URL).content.decode()
    assert "Sign in" in html
    # Story 10.4. In a server-rendered form this is a widget attribute, not a useEffect.
    assert "autofocus" in html
    assert 'name="email"' in html and 'name="password"' in html


@pytest.mark.django_db
def test_login_page_offers_no_sso_button() -> None:
    # The whole OIDC epic (17) is unimplemented; a non-functional SSO button would be worse
    # than none. Pinned so a later story does not add one before Epic 17 lands.
    html = Client().get(LOGIN_URL).content.decode().lower()
    for term in ["sso", "single sign-on", "oidc", "continue with"]:
        assert term not in html


@pytest.mark.django_db
def test_register_page_renders() -> None:
    html = Client().get(REGISTER_URL).content.decode()
    assert "Create account" in html
    assert 'name="email"' in html and 'name="password"' in html


# --- Login (AC #1, #3, #6) --------------------------------------------------------------


@pytest.mark.django_db
def test_valid_login_starts_a_session_and_lands_on_the_index(existing_user: None) -> None:
    client = Client()
    response = client.post(LOGIN_URL, {"email": "user@example.com", "password": PASSWORD})

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    assert SESSION_KEY in client.session


@pytest.mark.django_db
def test_login_returns_the_user_to_the_page_they_were_bounced_from(existing_user: None) -> None:
    """The full Story 10.2 round trip, through a real Story 21.4 mixin.

    Asserting the round trip end to end (rather than just that `next` is honoured) is what
    proves the mixin's redirect and the login form agree on the parameter name.
    """
    client = Client()

    # A protected page bounces an anonymous user to login, carrying the destination.
    bounced = client.get("/ui/orgs/switch/")
    assert bounced.status_code == 302
    location = bounced.headers["Location"]
    assert location.startswith(LOGIN_URL) and "next=" in location

    # The login page round-trips it through a hidden input...
    form_page = client.get(location)
    assert 'name="next"' in form_page.content.decode()

    # ...and signing in continues to the original destination.
    response = client.post(LOGIN_URL, {"email": "user@example.com", "password": PASSWORD, "next": "/ui/orgs/switch/"})
    assert response.headers["Location"] == "/ui/orgs/switch/"


@pytest.mark.django_db
def test_an_external_next_is_refused(existing_user: None) -> None:
    client = Client()
    response = client.post(
        LOGIN_URL,
        {"email": "user@example.com", "password": PASSWORD, "next": "https://evil.example.com/x"},
    )
    assert response.headers["Location"] == "/"


@pytest.mark.django_db
def test_wrong_password_re_renders_with_a_message_and_no_session(existing_user: None) -> None:
    client = Client()
    response = client.post(LOGIN_URL, {"email": "user@example.com", "password": "wrong-password"})

    assert response.status_code == 200  # re-rendered form, not a redirect
    assert INVALID_CREDENTIALS in response.content.decode()
    assert SESSION_KEY not in client.session


@pytest.mark.django_db
def test_the_password_field_is_cleared_after_a_failed_attempt(existing_user: None) -> None:
    # AC #6. PasswordInput does not re-render its value, so this needs no explicit handling
    # — but it is exactly the kind of thing a later refactor to a custom widget could break.
    response = Client().post(LOGIN_URL, {"email": "user@example.com", "password": "wrong-password"})
    assert "wrong-password" not in response.content.decode()


@pytest.mark.django_db
def test_unknown_email_is_indistinguishable_from_a_wrong_password(existing_user: None) -> None:
    """AC #6: the login form must not be an account-enumeration oracle."""
    wrong_password = Client().post(LOGIN_URL, {"email": "user@example.com", "password": "nope-nope-nope"})
    unknown_email = Client().post(LOGIN_URL, {"email": "nobody@example.com", "password": "nope-nope-nope"})

    assert wrong_password.status_code == unknown_email.status_code == 200
    # Not merely the same message — the same page once the CSRF token and the echoed email
    # are masked, so nothing (a count, an extra hint, a field-level marker on `email`)
    # distinguishes "no such account" from "wrong password".
    assert _body(wrong_password) == _body(unknown_email)
    assert INVALID_CREDENTIALS in wrong_password.content.decode()


@pytest.mark.django_db
def test_a_malformed_email_is_an_inline_field_error_not_a_banner(existing_user: None) -> None:
    # AC #1: errors attach to the offending field. A credential failure is form-level (it
    # cannot say which field), but a format error can and should point at the input.
    response = Client().post(LOGIN_URL, {"email": "not-an-email", "password": PASSWORD})
    html = response.content.decode()
    assert response.status_code == 200
    assert "Enter a valid email address." in html
    assert INVALID_CREDENTIALS not in html


@pytest.mark.django_db
def test_an_authenticated_user_is_sent_on_rather_than_shown_the_form(existing_user: None) -> None:
    client = Client()
    client.post(LOGIN_URL, {"email": "user@example.com", "password": PASSWORD})
    assert client.get(LOGIN_URL).status_code == 302


# --- Registration (AC #1, #2, #6) -------------------------------------------------------


@pytest.mark.django_db
def test_registration_creates_the_account_with_no_org_and_redirects_to_login() -> None:
    client = Client()
    response = client.post(REGISTER_URL, {"email": "new@example.com", "password": PASSWORD})

    assert response.status_code == 302
    assert response.headers["Location"] == LOGIN_URL
    user = user_model().objects.get(email="new@example.com")
    # Story 2.6: registration creates NO organisation.
    assert OrgMembership.objects.filter(user=user).count() == 0
    # Not signed in by registering — they are sent to sign in (Story 10.3).
    assert SESSION_KEY not in client.session


@pytest.mark.django_db
def test_registration_flashes_a_message_visible_after_the_redirect() -> None:
    client = Client()
    client.post(REGISTER_URL, {"email": "flash@example.com", "password": PASSWORD})
    assert "Account created. Please sign in." in client.get(LOGIN_URL).content.decode()


@pytest.mark.django_db
def test_a_new_user_sees_the_shared_no_org_state(existing_user: None) -> None:
    # AC #2's consequence: registration makes a zero-org user, who gets the Story 21.4
    # empty state rather than an error.
    client = Client()
    client.post(REGISTER_URL, {"email": "zero@example.com", "password": PASSWORD})
    client.post(LOGIN_URL, {"email": "zero@example.com", "password": PASSWORD})
    # /ui/ is not org-gated, so probe a page that is — via the switcher's absence and the
    # shell rendering without an active org.
    html = client.get("/ui/").content.decode()
    assert 'id="org-switcher"' not in html


@pytest.mark.django_db
def test_duplicate_email_is_a_field_error_not_a_server_error(existing_user: None) -> None:
    response = Client().post(REGISTER_URL, {"email": "user@example.com", "password": PASSWORD})

    assert response.status_code == 200  # not a 500 from a unique-constraint violation
    assert "An account with this email already exists." in response.content.decode()
    assert user_model().objects.filter(email__iexact="user@example.com").count() == 1


@pytest.mark.django_db
def test_duplicate_email_is_case_insensitive(existing_user: None) -> None:
    response = Client().post(REGISTER_URL, {"email": "USER@example.com", "password": PASSWORD})
    assert "An account with this email already exists." in response.content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("password", "expected"),
    [
        ("short", "too short"),
        ("12345678901", "entirely numeric"),
        ("password", "too common"),
    ],
)
def test_configured_password_validators_render_inline(password: str, expected: str) -> None:
    """AUTH_PASSWORD_VALIDATORS surface per-field, which the SPA could not do at all."""
    response = Client().post(REGISTER_URL, {"email": "weak@example.com", "password": password})

    assert response.status_code == 200
    assert expected in response.content.decode()
    assert not user_model().objects.filter(email="weak@example.com").exists()


@pytest.mark.django_db
def test_a_password_similar_to_the_email_is_rejected() -> None:
    # UserAttributeSimilarityValidator only fires when given a user instance; passing None
    # would silently skip it, so this pins that the form builds a probe instance.
    response = Client().post(REGISTER_URL, {"email": "wonderland@example.com", "password": "wonderland"})
    assert "too similar" in response.content.decode()


# --- Logout (AC #5) ---------------------------------------------------------------------


@pytest.mark.django_db
def test_logout_invalidates_the_session_and_returns_to_the_index(existing_user: None) -> None:
    client = Client()
    client.post(LOGIN_URL, {"email": "user@example.com", "password": PASSWORD})
    assert SESSION_KEY in client.session

    response = client.post(LOGOUT_URL)

    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    # The session must be gone, not merely redirected away from.
    assert SESSION_KEY not in client.session


@pytest.mark.django_db
def test_logout_rejects_get(existing_user: None) -> None:
    client = Client()
    client.post(LOGIN_URL, {"email": "user@example.com", "password": PASSWORD})
    assert client.get(LOGOUT_URL).status_code == 405
    assert SESSION_KEY in client.session  # and the session survives the attempt


@pytest.mark.django_db
def test_logout_without_a_csrf_token_is_rejected(existing_user: None) -> None:
    client = Client(enforce_csrf_checks=True)
    assert client.login(email="user@example.com", password=PASSWORD)

    assert client.post(LOGOUT_URL).status_code == 403
    assert SESSION_KEY in client.session


@pytest.mark.django_db
def test_the_account_menu_shows_the_email_and_a_post_logout(existing_user: None) -> None:
    client = Client()
    client.post(LOGIN_URL, {"email": "user@example.com", "password": PASSWORD})
    html = client.get("/ui/").content.decode()

    assert "user@example.com" in html
    # A form posting to the HTML logout route — not an <a href> and not the DRF endpoint.
    assert f'action="{LOGOUT_URL}"' in html
    assert 'action="/api/v1/auth/logout/"' not in html


@pytest.mark.django_db
def test_the_shell_links_anonymous_visitors_to_the_html_login_page() -> None:
    html = Client().get("/ui/").content.decode()
    assert f'href="{LOGIN_URL}"' in html
    assert 'href="/api/v1/auth/login/"' not in html
