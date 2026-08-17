"""Story 21.1 AC #4: assert the settings-derived filesystem paths.

`BASE_DIR` moved from `backend/` to the repository root when the tree became a
`src/` layout, which means the `parent` chain in `config/settings/base.py` gained a
fourth hop. An off-by-one there does NOT raise — it silently relocates the SQLite
database, `media/`, `staticfiles/`, and the Celery beat schedule to a sibling
directory. That is the whole reason these assertions exist rather than a visual
check of the settings module.

Pure settings introspection: no filesystem writes, no database, no network.
"""

from pathlib import Path

from django.conf import settings

# tests/unit/<this file> -> tests -> repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]

# Captured at IMPORT time, which is during collection — before any test triggers
# pytest-django's session-scoped database setup. That setup rewrites
# DATABASES["default"]["NAME"] in place to a shared in-memory SQLite URI
# ("file:memorydb_default?mode=memory&cache=shared"), permanently, for the rest of the
# session. Reading it inside the test body therefore cannot see the configured value.
_CONFIGURED_DB_NAME = settings.DATABASES["default"]["NAME"]


def test_base_dir_is_the_repository_root() -> None:
    # The repo root is identifiable by the files only it carries.
    assert settings.BASE_DIR == REPO_ROOT
    assert (settings.BASE_DIR / "pyproject.toml").is_file()
    assert (settings.BASE_DIR / "pixi.toml").is_file()
    assert (settings.BASE_DIR / "manage.py").is_file()


def test_base_dir_is_not_the_src_directory() -> None:
    # The specific off-by-one this guards: three `parent` hops instead of four
    # lands on src/, which also contains a `config` directory and so looks plausible.
    assert settings.BASE_DIR.name != "src"
    assert (settings.BASE_DIR / "src").is_dir()


def test_apps_dir_is_the_host_project_package() -> None:
    assert settings.APPS_DIR == REPO_ROOT / "src" / "django_service"
    assert (settings.APPS_DIR / "__init__.py").is_file()


def test_reusable_app_lives_under_the_path_root() -> None:
    path_root = settings.BASE_DIR / "src" / "django_apps"
    assert (path_root / "inventory" / "__init__.py").is_file()
    # Reference AD-6: the path root is a path root, not a package. An __init__.py here
    # would make the app importable as `django_apps.inventory` and defeat the layout.
    assert not (path_root / "__init__.py").exists()


def test_static_root_resolves_under_the_repository_root() -> None:
    assert settings.STATIC_ROOT == REPO_ROOT / "staticfiles"


def test_media_root_resolves_under_the_repository_root() -> None:
    assert settings.MEDIA_ROOT == REPO_ROOT / "media"


def test_default_sqlite_path_resolves_under_the_repository_root() -> None:
    # The test settings inherit the base default (no DATABASE_URL in the env).
    assert _CONFIGURED_DB_NAME == str(REPO_ROOT / "db.sqlite3")


def test_frontend_dist_resolves_to_the_repo_root_frontend() -> None:
    # AC #8: the SPA must keep working. BASE_DIR is now the repo root itself, so this
    # path takes no `.parent` hop — a stale `.parent` would point outside the repo.
    assert settings.FRONTEND_DIST == REPO_ROOT / "frontend" / "dist"
    assert settings.SPA_INDEX_FILE == REPO_ROOT / "frontend" / "dist" / "index.html"
