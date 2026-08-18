"""Story 21.24: nothing in the app requires a login (AC #1), and the gate is gone (AC #2).

The app deliberately has **no authentication of its own**. Identity becomes the host
platform's responsibility, supplied via OIDC and group claims when `inventory` is
contributed to it (Epics 17-18). Until then every page and every endpoint is open.

Routes are enumerated from the **urlconf**, not from a hand-written list. A hand-written
list silently stops covering routes added later, which is exactly how a page ships with a
gate nobody meant to add.

What is *not* removed, and is asserted here too: org isolation (AD-2) still refuses another
org's object, and CSRF still protects the mutating endpoints. This story removed *who you
are*, not *what a browser may be made to do on your behalf*.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

import pytest
from django.test import Client
from django.urls import URLPattern, URLResolver, get_resolver

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.models import Org

SRC = Path(__file__).resolve().parents[2] / "src"

#: Path parameters get a value that resolves; the point is the gate, not the lookup.
SAMPLE = {"task_id": "00000000-0000-0000-0000-000000000000", "kind": "sbom"}


def _routes() -> list[str]:
    """Every concrete GET-able URL in the project, taken from the resolver."""
    found: list[str] = []

    def walk(patterns: list[Any], prefix: str) -> None:
        for entry in patterns:
            if isinstance(entry, URLResolver):
                walk(list(entry.url_patterns), prefix + str(entry.pattern))
            elif isinstance(entry, URLPattern):
                found.append(prefix + str(entry.pattern))

    walk(list(get_resolver().url_patterns), "")
    return found


def _concrete(route: str) -> str | None:
    """Turn a urlconf pattern into a requestable path, or None if it cannot be."""
    import re

    if route.startswith("api/schema") or route.startswith("admin/"):
        return None  # Django's admin keeps its own login; the schema view is not a page.
    path = "/" + route
    for name, value in SAMPLE.items():
        path = re.sub(rf"<[^:>]*:?{name}>", value, path)
    if "<" in path:
        return None
    return path


PAGE_ROUTES = [p for p in (_concrete(r) for r in _routes()) if p]


# --- AC #1: no route refuses an anonymous caller ---------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", PAGE_ROUTES)
def test_no_route_redirects_an_anonymous_caller_to_a_login_page(path: str) -> None:
    response = Client().get(path)

    if response.status_code in (301, 302):
        location = response["Location"]
        assert "login" not in location.lower(), f"{path} still redirects to a login page"


@pytest.mark.django_db
@pytest.mark.parametrize("path", PAGE_ROUTES)
def test_no_route_forbids_an_anonymous_caller(path: str) -> None:
    """403 is the shape the deleted access control produced; nothing should emit it now."""
    assert Client().get(path).status_code != 403, f"{path} still 403s"


@pytest.mark.django_db
def test_every_page_route_is_actually_reachable(default_org: Org) -> None:
    """Stronger than "not 403": every nav destination must render.

    A page that 500s or 404s would satisfy the two tests above while being just as broken.
    """
    for path in ("/", "/upload", "/history", "/keys"):
        assert Client().get(path).status_code == 200, path


@pytest.mark.django_db
def test_the_api_serves_an_anonymous_caller(default_org: Org) -> None:
    """`DEFAULT_PERMISSION_CLASSES` is `AllowAny`; the API-key path is unaffected."""
    for path in ("/api/v1/orgs/me/", "/api/v1/orgs/", "/api/v1/sbom/jobs/", "/api/v1/keys/"):
        assert Client().get(path).status_code == 200, path


@pytest.mark.django_db
def test_auth_me_answers_for_an_anonymous_caller(default_org: Org) -> None:
    """Kept in the frozen contract (AC #9); it must report a null identity, not 500."""
    body = Client().get("/api/v1/auth/me/").json()

    assert body == {"id": None, "email": None, "is_admin": True, "is_global_admin": True}


# --- AC #2: the access-control layer is deleted, not disabled --------------------------


@pytest.mark.parametrize(
    "name", ["OrgMemberRequiredMixin", "OrgAdminRequiredMixin", "GlobalAdminRequiredMixin", "NO_ORG_TEMPLATE"]
)
def test_the_access_control_names_no_longer_exist(name: str) -> None:
    """A deletion story needs a test that fails if the code comes back."""
    access = importlib.import_module("inventory.common.access")

    assert not hasattr(access, name), f"{name} is back in inventory.common.access"


def test_no_source_file_imports_djangos_auth_mixins() -> None:
    """`LoginRequiredMixin` and friends are how the gate would most easily reappear."""
    offenders = [
        str(path.relative_to(SRC))
        for path in SRC.rglob("*.py")
        if "django.contrib.auth.mixins" in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"auth mixins imported by: {offenders}"


def test_the_deleted_auth_surface_is_gone() -> None:
    from inventory.users import pages, views

    for name in ("LoginPageView", "RegisterPageView", "LogoutPageView"):
        assert not hasattr(pages, name), name
    for name in ("LoginView", "LogoutView", "RegisterView"):
        assert not hasattr(views, name), name
    # AuthMeView stays: it is part of the frozen /api/v1/ contract (AC #9).
    assert hasattr(views, "AuthMeView")


def test_the_zero_org_template_is_deleted() -> None:
    assert not (SRC / "django_service" / "templates" / "_no_org.html").exists()


def test_no_login_redirect_settings_remain() -> None:
    from django.conf import settings

    # Django supplies its own defaults, so absence is asserted against the project module.
    project_settings = (SRC / "config" / "settings" / "base.py").read_text(encoding="utf-8")
    for name in ("LOGIN_URL", "LOGIN_REDIRECT_URL", "LOGOUT_REDIRECT_URL"):
        assert f"\n{name} =" not in project_settings, name
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == ["rest_framework.permissions.AllowAny"]


# --- AC #3: tenancy is not authentication, and it survives ------------------------------


@pytest.mark.django_db
def test_another_orgs_job_is_still_indistinguishable_from_a_missing_one(default_org: Org) -> None:
    """The one place a denial is still expected.

    AD-2 is a tenancy invariant, not an authentication one. An anonymous caller acts as the
    default org and must not be able to read a job belonging to another org — and must not
    be able to tell the difference between "not yours" and "does not exist".
    """
    other = Org.objects.create(name="Other", slug="other")
    upload = ManifestUpload.objects.create(
        org=other,
        file="manifest-uploads/t/f.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
    )
    job = SBOMJob.objects.create(
        org=other,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.SUCCESS,
        summary_stats={},
        result_key="sboms/x.json",
    )
    client = Client()

    cross_org = client.get(f"/results/{job.task_id}")
    nonexistent = client.get("/results/11111111-1111-1111-1111-111111111111")

    assert cross_org.status_code == 404
    assert nonexistent.status_code == 404


@pytest.mark.django_db
def test_another_orgs_job_is_absent_from_history(default_org: Org) -> None:
    other = Org.objects.create(name="Other", slug="other")
    upload = ManifestUpload.objects.create(
        org=other,
        file="manifest-uploads/t/f.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
    )
    job = SBOMJob.objects.create(
        org=other, manifest=upload, output_format="cyclonedx-json", status=SBOMJob.Status.SUCCESS, summary_stats={}
    )

    assert str(job.task_id) not in Client().get("/history").content.decode()


# --- CSRF is not authentication and was not removed with it -----------------------------


@pytest.mark.django_db
def test_the_org_switcher_still_requires_csrf(default_org: Org) -> None:
    """Removing the login requirement must not turn a state-mutating POST into an open one."""
    client = Client(enforce_csrf_checks=True)

    response = client.post("/ui/orgs/switch/", {"slug": default_org.slug})

    assert response.status_code == 403


@pytest.mark.django_db
def test_the_org_switcher_still_refuses_a_get(default_org: Org) -> None:
    # A GET-reachable switch could be triggered by any link, image, or prefetcher.
    assert Client().get("/ui/orgs/switch/").status_code == 405
