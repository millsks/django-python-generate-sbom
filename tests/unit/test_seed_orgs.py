"""Story 22.10: seeding the deployment's organizations from a committed list.

Organizations are lines of business, known up front. Seeding them beats a creation form: a
typed name gets typos, near-duplicates, and slugs nobody chose, and a file is reviewable in a
pull request.

The command runs on every boot (Compose: `migrate && seed-orgs && seed-superuser && web`), so
**idempotence is the load-bearing property** — and the tests treat it that way rather than
checking it once in passing.
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from inventory.users.models import Org

COMMAND = "seed_orgs"


def _write_list(path: Path, body: str) -> str:
    path.write_text(body, encoding="utf-8")
    return str(path)


@pytest.fixture
def org_list(tmp_path: Path, settings: pytest.FixtureRequest) -> Path:
    """A two-org list, pointed at by the setting the command reads."""
    path = tmp_path / "orgs.yml"
    _write_list(
        path,
        "organizations:\n  - name: Retail Banking\n    slug: retail-banking\n"
        "  - name: Capital Markets\n    slug: capital-markets\n",
    )
    settings.INVENTORY_ORGS_FILE = str(path)  # type: ignore[attr-defined]
    return path


def _run(*args: str) -> str:
    out = StringIO()
    call_command(COMMAND, *args, stdout=out)
    return out.getvalue()


# --- Seeding, and doing nothing the second time -------------------------------------------


@pytest.mark.django_db
def test_it_creates_the_listed_organizations(org_list: Path) -> None:
    _run()

    assert Org.objects.filter(slug="retail-banking", name="Retail Banking").exists()
    assert Org.objects.filter(slug="capital-markets").exists()


@pytest.mark.django_db
def test_running_twice_creates_nothing_the_second_time(org_list: Path) -> None:
    """The property the boot sequence depends on."""
    _run()
    before = Org.objects.count()

    output = _run()

    assert Org.objects.count() == before
    assert "already exists" in output


@pytest.mark.django_db
def test_adding_a_line_seeds_only_the_new_one(org_list: Path) -> None:
    """Growing the list is the normal edit; it must not disturb what is already there."""
    _run()
    existing = Org.objects.get(slug="retail-banking")
    org_list.write_text(org_list.read_text(encoding="utf-8") + "  - name: Wealth\n    slug: wealth\n", encoding="utf-8")

    output = _run()

    assert Org.objects.filter(slug="wealth").exists()
    assert "1 to create" in output
    assert Org.objects.get(slug="retail-banking").pk == existing.pk


@pytest.mark.django_db
def test_removing_a_line_deletes_nothing(org_list: Path) -> None:
    """Deleting an org would orphan its jobs and artifacts — a deliberate act, not a file edit."""
    _run()
    _write_list(org_list, "organizations:\n  - name: Retail Banking\n    slug: retail-banking\n")

    _run()

    assert Org.objects.filter(slug="capital-markets").exists()


# --- The slug is the identity ---------------------------------------------------------------


@pytest.mark.django_db
def test_a_renamed_org_is_reported_but_not_rewritten(org_list: Path) -> None:
    """`INVENTORY_DEFAULT_ORG_SLUG`, the switcher, and API keys all reference the slug.

    Silently rewriting the display name on every boot would make the database follow the file
    with no record; refusing to say anything would hide the divergence. So it reports.
    """
    _run()
    _write_list(
        org_list,
        "organizations:\n  - name: Retail Bank\n    slug: retail-banking\n"
        "  - name: Capital Markets\n    slug: capital-markets\n",
    )

    output = _run()

    assert "name differs for 'retail-banking'" in output
    assert Org.objects.get(slug="retail-banking").name == "Retail Banking"


@pytest.mark.django_db
def test_dry_run_writes_nothing(org_list: Path) -> None:
    output = _run("--dry-run")

    assert "would create retail-banking" in output
    assert "nothing was written" in output
    assert not Org.objects.filter(slug="retail-banking").exists()


# --- A bad list stops the boot rather than half-seeding it ----------------------------------


@pytest.mark.django_db
def test_the_reserved_admin_slug_is_refused(tmp_path: Path, settings: pytest.FixtureRequest) -> None:
    """The ADMIN org is a platform tier, not a workspace (Stories 2.12/2.18).

    Seeding one here would create a second row that the switcher and `get_request_org` both
    deliberately refuse to treat as a workspace — an org nobody could ever act as.
    """
    path = _write_list(tmp_path / "orgs.yml", "organizations:\n  - name: Admin\n    slug: admin\n")
    settings.INVENTORY_ORGS_FILE = path  # type: ignore[attr-defined]

    with pytest.raises(CommandError, match="reserved slug"):
        _run()


@pytest.mark.django_db
def test_a_duplicate_slug_is_refused(tmp_path: Path, settings: pytest.FixtureRequest) -> None:
    path = _write_list(
        tmp_path / "orgs.yml",
        "organizations:\n  - name: One\n    slug: dup\n  - name: Two\n    slug: dup\n",
    )
    settings.INVENTORY_ORGS_FILE = path  # type: ignore[attr-defined]

    with pytest.raises(CommandError, match="duplicate slug"):
        _run()


@pytest.mark.django_db
def test_an_entry_missing_its_slug_is_refused(tmp_path: Path, settings: pytest.FixtureRequest) -> None:
    path = _write_list(tmp_path / "orgs.yml", "organizations:\n  - name: No Slug\n")
    settings.INVENTORY_ORGS_FILE = path  # type: ignore[attr-defined]

    with pytest.raises(CommandError, match="needs both"):
        _run()


@pytest.mark.django_db
def test_a_missing_file_is_refused_with_the_path(tmp_path: Path, settings: pytest.FixtureRequest) -> None:
    settings.INVENTORY_ORGS_FILE = str(tmp_path / "absent.yml")  # type: ignore[attr-defined]

    with pytest.raises(CommandError, match="Org list not found"):
        _run()


@pytest.mark.django_db
def test_malformed_yaml_is_refused(tmp_path: Path, settings: pytest.FixtureRequest) -> None:
    path = _write_list(tmp_path / "orgs.yml", "organizations: [unclosed\n")
    settings.INVENTORY_ORGS_FILE = path  # type: ignore[attr-defined]

    with pytest.raises(CommandError, match="not valid YAML"):
        _run()


@pytest.mark.django_db
def test_a_bad_entry_seeds_nothing_at_all(tmp_path: Path, settings: pytest.FixtureRequest) -> None:
    """Validation happens before any write: a half-seeded tenant list is the worst outcome.

    Jobs would start landing in whichever orgs happened to exist, which is harder to notice and
    to undo than a boot that stopped.
    """
    path = _write_list(
        tmp_path / "orgs.yml",
        "organizations:\n  - name: Good\n    slug: good\n  - name: Bad\n",
    )
    settings.INVENTORY_ORGS_FILE = path  # type: ignore[attr-defined]

    with pytest.raises(CommandError):
        _run()

    assert not Org.objects.filter(slug="good").exists()


# --- The committed list itself ---------------------------------------------------------------


def test_the_repository_list_is_valid() -> None:
    """The shipped `orgs.yml` must parse, or the Compose boot sequence fails on first run."""
    from inventory.management.commands.seed_orgs import load_org_specs

    specs = load_org_specs(Path(__file__).resolve().parents[2] / "orgs.yml")

    assert specs, "orgs.yml should list at least one organization"
    assert all(spec["slug"] and spec["name"] for spec in specs)
    assert len({spec["slug"] for spec in specs}) == len(specs)
