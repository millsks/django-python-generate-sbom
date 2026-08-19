"""Story 22.1: the plainly-named environment template must be the containerless one.

The bug was a **filename**. `.env.example` — the file a newcomer copies by name, and the one
`README.md` told them to copy — selected `config.settings.production` and named PostgreSQL,
Redis, and MinIO. A developer without Docker got a stack that could not start, failing with a
PostgreSQL connection refusal that pointed nowhere near the cause. Docker and Podman are
unavailable on Windows under the destination organization's security policy, so that was not a
minor inconvenience for part of the team; it was the only local path, broken.

These tests assert on **both** templates. Checking only that `.env.example` is containerless
would pass just as happily if someone emptied the container template, and checking only that it
avoids Postgres would pass against an empty file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE = REPO / ".env.example"
CONTAINER_TEMPLATE = REPO / ".env.container.example"

#: Settings and services that only exist when something is running them. Any of these in the
#: default template means a fresh clone is pointed at infrastructure it has to provide.
CONTAINER_ONLY_KEYS = ("DATABASE_URL", "REDIS_URL", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
OBJECT_STORE_KEYS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_STORAGE_BUCKET_NAME", "MINIO_ROOT_USER")


def _assignments(path: Path) -> dict[str, str]:
    """Parse `KEY=value` lines, ignoring comments and blanks.

    Comments are skipped deliberately: both templates *mention* the other's services in prose
    to explain the split, and a naive substring search would flag that explanation as the bug.
    """
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        values[key.strip()] = value.strip()
    return values


# --- AC #1 + #4: the default template is containerless ------------------------------------


def test_the_default_template_selects_local_settings() -> None:
    assert _assignments(DEFAULT_TEMPLATE)["DJANGO_SETTINGS_MODULE"] == "config.settings.local"


@pytest.mark.parametrize("key", CONTAINER_ONLY_KEYS + OBJECT_STORE_KEYS)
def test_the_default_template_sets_no_container_only_key(key: str) -> None:
    """These must stay UNSET so the SQLite and filesystem-storage defaults apply.

    Setting one is not a harmless extra: it silently opts a fresh clone into infrastructure
    the developer then has to run, which is exactly the failure this story removed.
    """
    assert key not in _assignments(DEFAULT_TEMPLATE), (
        f"{key} is set in .env.example, which opts local dev into a service it must then run"
    )


def test_the_default_template_still_carries_the_app_settings() -> None:
    """Containerless must not mean empty — the app's own settings still belong here."""
    values = _assignments(DEFAULT_TEMPLATE)

    for key in ("SECRET_KEY", "ALLOWED_HOSTS", "INVENTORY_DEFAULT_ORG_SLUG", "SBOM_MAX_CONCURRENT_JOBS_PER_ORG"):
        assert key in values, key


# --- AC #2: the container template still exists and is still complete ---------------------


def test_the_container_template_selects_production_settings() -> None:
    assert _assignments(CONTAINER_TEMPLATE)["DJANGO_SETTINGS_MODULE"] == "config.settings.production"


@pytest.mark.parametrize("key", CONTAINER_ONLY_KEYS + OBJECT_STORE_KEYS)
def test_the_container_template_still_configures_every_service(key: str) -> None:
    """The inverse of the test above — so the two templates cannot be swapped back silently."""
    assert key in _assignments(CONTAINER_TEMPLATE), f"{key} is missing from .env.container.example"


def test_the_container_template_does_not_enable_debug() -> None:
    """It selects production settings; a template that does should not also switch DEBUG on.

    The discarded duplicate had `DEBUG=True` alongside production settings. Keeping that
    combination available invites someone to copy it somewhere it matters.
    """
    assert _assignments(CONTAINER_TEMPLATE)["DEBUG"] == "False"


def test_the_container_template_keeps_the_presigned_endpoint_note() -> None:
    """A real trap, documented in only one of the two former duplicates.

    Presigned download URLs point at the internal `minio:9000`, which a browser on the host
    cannot resolve. That comment survived the reshuffle; losing it would re-bury a problem
    somebody already spent time on.
    """
    assert "AWS_S3_ENDPOINT" in CONTAINER_TEMPLATE.read_text(encoding="utf-8")


# --- No third copy ------------------------------------------------------------------------


def test_there_are_exactly_two_env_templates() -> None:
    """`.env.local.example` was a duplicate of the containerless config under a second name.

    Three templates — two of which differed only by `DEBUG` and one comment — is the same
    confusion in another place. A new one should not appear without a reason.
    """
    found = sorted(p.name for p in REPO.glob(".env*.example"))

    assert found == [".env.container.example", ".env.example"], found


def test_the_readme_tells_a_newcomer_to_copy_the_containerless_template() -> None:
    """The filename was only half the bug; the README's instruction was the other half."""
    readme = (REPO / "README.md").read_text(encoding="utf-8")

    assert "cp .env.example .env" in readme
    # The Compose path must name the other one explicitly rather than inheriting the default.
    assert "cp .env.container.example .env" in readme
