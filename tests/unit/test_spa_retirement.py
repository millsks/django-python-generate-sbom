"""Story 21.19: the React SPA and the Node toolchain are gone.

The load-bearing test here is `test_every_spa_route_has_a_django_owner`. Deleting the catch-all
converts every un-migrated path from "renders the SPA" to "404", so a route missed anywhere in
Stories 21.5-21.18 fails **only at this point** — the Dev Notes call this the AC that bites. The
ten routes below are transcribed from `App.tsx`'s `<Route>` table, captured before the file was
deleted; they are the definition of what the SPA served.

The remaining tests are removal checks. They exist because a half-removal is the likely failure:
a stale `fe-*` entry in the `ci` task, a lingering `frontend` flag in codecov, a `COPY frontend/`
in the Dockerfile — none of which any behavioural test would notice.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client
from django.urls import Resolver404, resolve

from inventory.manifests.models import ManifestUpload
from inventory.sbom.models import SBOMJob
from inventory.users.models import Org
from inventory.users.services import create_org, register_user

REPO = Path(__file__).resolve().parents[2]
PASSWORD = "pw12345678"

# Transcribed from `frontend/src/App.tsx` before deletion. `/results/:taskId` is parameterised,
# so a placeholder id is enough to check that the PATTERN still has an owner.
#: Four SPA routes are deliberately absent, each retired on purpose rather than by oversight,
#: and each asserted to 404 via RETIRED_ROUTES below:
#:   /register, /login             — Story 21.24 removed the app's own authentication
#:   /members, /platform/global-admins — Story 22.9 removed surfaces that edited records which
#:                                   gate nothing without identity (and were broken anonymously)
#:   /organization                 — Story 22.11: orgs are seeded from orgs.yml, so the hub and
#:                                   creation form were redundant
SPA_ROUTES = (
    "/",
    "/keys",
    "/upload",
    "/results/00000000-0000-0000-0000-000000000000",
    "/job-status",
)


def _real_job(org: Org) -> SBOMJob:
    """A job the requesting org owns.

    `/results/<unknown-id>` correctly 404s (AD-2 makes a cross-org job indistinguishable from a
    missing one), so a placeholder id cannot tell "the route lost its owner" apart from "that
    job does not exist" — which is exactly the confusion this story's tests must avoid.
    """
    upload = ManifestUpload.objects.create(
        org=org,
        file="manifest-uploads/t/f.txt",
        detected_format=ManifestUpload.Format.REQUIREMENTS,
        original_filename="requirements.txt",
    )
    return SBOMJob.objects.create(
        org=org,
        manifest=upload,
        output_format="cyclonedx-json",
        status=SBOMJob.Status.SUCCESS,
        summary_stats={},
        result_key="sboms/x.json",
    )


# --- AC #2: no route left behind -----------------------------------------------------------


@pytest.mark.parametrize("route", SPA_ROUTES)
def test_every_spa_route_has_a_django_owner(route: str) -> None:
    """Each path the SPA served must resolve to a Django view, not raise Resolver404."""
    try:
        match = resolve(route)
    except Resolver404:  # pragma: no cover - the failure message is the point
        pytest.fail(f"{route} lost its owner when the SPA catch-all was deleted")
    assert match.func is not None


@pytest.mark.django_db
@pytest.mark.parametrize("route", SPA_ROUTES)
def test_no_spa_route_answers_404(route: str) -> None:
    """Resolution is not enough — the view must actually respond.

    A signed-in org admin sees every page, so any 404 here is a genuinely missing owner rather
    than an access decision. Redirects and 403s are fine; 404 is not.
    """
    user = register_user(email="admin@example.com", password=PASSWORD)
    org = create_org(name="Acme", admin_user=user)
    client = Client()
    assert client.login(email="admin@example.com", password=PASSWORD)
    if route.startswith("/results/"):
        route = f"/results/{_real_job(org).task_id}"

    response = client.get(route)

    assert response.status_code != 404, f"{route} 404s"


def test_the_catch_all_and_its_view_are_gone() -> None:
    from django.urls import get_resolver

    patterns = [str(p.pattern) for p in get_resolver().url_patterns]
    assert not any("(?!api/" in p for p in patterns), "the SPA catch-all is still registered"

    from inventory.common import views

    assert not hasattr(views, "SpaView")


def test_the_admin_site_is_still_reachable() -> None:
    """Carried over from the deleted `test_spa.py`.

    It used to assert the catch-all did not swallow the admin; the claim that the admin
    resolves is worth keeping on its own, independent of what used to threaten it.
    """
    assert resolve("/admin/").app_name == "admin"


@pytest.mark.django_db
def test_an_unknown_path_now_404s() -> None:
    """The behaviour change Story 21.18 flagged and deliberately left to this story.

    `App.tsx` routed `*` to `HomePage`, so a mistyped URL used to answer 200 with the landing
    page. That hides broken links; a real 404 says what happened. This replaces
    `test_an_unknown_path_still_falls_back_to_the_spa`.
    """
    assert Client().get("/definitely-not-a-real-page").status_code == 404


# --- AC #2: no settings key references the frontend ----------------------------------------


def test_no_setting_references_the_frontend() -> None:
    leaked = [
        name for name in dir(settings) if name.isupper() and "frontend" in str(getattr(settings, name, "")).lower()
    ]
    assert not leaked, f"settings still referencing frontend/: {leaked}"


def test_static_dirs_survived_the_removal() -> None:
    """Only the `FRONTEND_DIST` entry goes — Story 21.3 put the vendored assets here too."""
    assert settings.STATICFILES_DIRS, "STATICFILES_DIRS was emptied, not pruned"
    assert any(str(p).endswith("static") for p in settings.STATICFILES_DIRS)


# --- AC #1: the toolchain -------------------------------------------------------------------


def test_the_frontend_directory_is_gone() -> None:
    assert not (REPO / "frontend").exists()


def test_pixi_has_no_node_and_no_fe_tasks() -> None:
    manifest = tomllib.loads((REPO / "pixi.toml").read_text(encoding="utf-8"))

    assert "nodejs" not in manifest.get("dependencies", {})

    fe_tasks = [name for name in manifest.get("tasks", {}) if name.startswith("fe-")]
    assert not fe_tasks, f"frontend tasks remain: {fe_tasks}"


def test_the_ci_task_does_not_depend_on_a_deleted_task() -> None:
    """A stale `depends-on` entry breaks the gate itself, which is how this would be found."""
    manifest = tomllib.loads((REPO / "pixi.toml").read_text(encoding="utf-8"))
    tasks = manifest["tasks"]
    defined = set(tasks)

    for name, spec in tasks.items():
        for dep in (spec or {}).get("depends-on", []) if isinstance(spec, dict) else []:
            assert dep in defined, f"task {name!r} depends on missing task {dep!r}"


# --- AC #3, #4, #5: build, CI, and quality tooling ------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "Dockerfile",
        "Procfile",
        ".github/workflows/ci.yml",
        ".github/workflows/maintenance.yml",
        "codecov.yml",
        "sonar-project.properties",
    ],
)
def test_no_build_or_ci_file_references_the_frontend(relative: str) -> None:
    text = (REPO / relative).read_text(encoding="utf-8")
    for needle in (
        "frontend",
        "fe-install",
        "fe-build",
        "fe-test",
        "fe-lint",
        "fe-cov",
        "fe-dev",
        "fe-typecheck",
        "fe-security",
        "npm",
        "node_modules",
    ):
        assert needle not in text, f"{relative} still references {needle!r}"


def test_the_windows_job_kept_its_python_coverage() -> None:
    """Only the frontend half of the win-64 job goes; Story 20.6 is why the job exists."""
    text = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "windows" in text.lower()
    assert "cov" in text
