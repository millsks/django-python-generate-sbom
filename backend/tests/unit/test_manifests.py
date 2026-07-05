"""Tests for manifest upload, format detection, and validation (Story 3.1)."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from generate_sbom.manifests.detection import UnsupportedFormatError, detect_format
from generate_sbom.manifests.models import ManifestUpload
from generate_sbom.users.services import create_org, register_user

META = {
    "application_id": "APP-1",
    "component_name": "web",
    "repository_url": "https://github.com/acme/web",
    "source_branch": "release",
}


@pytest.fixture(autouse=True)
def _tmp_media(settings: pytest.FixtureRequest, tmp_path: object) -> None:
    """Store uploaded files under a per-test temp dir, not the repo."""
    settings.MEDIA_ROOT = str(tmp_path)  # type: ignore[attr-defined]


def _login() -> APIClient:
    user = register_user(email="alice@example.com", password="pw12345678")
    create_org(name="alice", admin_user=user)
    client = APIClient()
    client.post(
        "/api/v1/auth/login/",
        {"email": "alice@example.com", "password": "pw12345678"},
        format="json",
    )
    return client


def _upload(client: APIClient, filename: str, content: bytes, **overrides: str) -> object:
    file = SimpleUploadedFile(filename, content, content_type="text/plain")
    return client.post(
        "/api/v1/manifests/upload/",
        {"file": file, **META, **overrides},
        format="multipart",
    )


@pytest.mark.django_db
def test_upload_stores_manifest_with_provenance() -> None:
    response = _upload(_login(), "requirements.txt", b"django==5.2\nrequests==2.32.3\n")

    assert response.status_code == 201
    assert response.data["detected_format"] == "requirements"
    upload = ManifestUpload.objects.get(pk=response.data["upload_id"])
    assert upload.application_id == "APP-1"
    assert upload.component_name == "web"
    assert upload.repository_url == "https://github.com/acme/web"
    assert upload.source_branch == "release"
    assert upload.file.name.startswith(f"manifest-uploads/{upload.org_id}/")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("filename", "content", "expected"),
    [
        ("pyproject.toml", b"[project]\nname = 'x'\n", "pyproject"),
        ("pixi.toml", b"[project]\nname = 'x'\n", "pixi_toml"),
        ("pixi.lock", b"version: 5\nenvironments: {}\n", "pixi_lock"),
        ("environment.yml", b"name: env\ndependencies: []\n", "conda"),
    ],
)
def test_format_detection(filename: str, content: bytes, expected: str) -> None:
    response = _upload(_login(), filename, content)
    assert response.status_code == 201
    assert response.data["detected_format"] == expected


@pytest.mark.parametrize(
    "filename",
    [
        "requirements.txt",
        "REQUIREMENTS.TXT",
        "requirements-dev.txt",
        "requirements_test.txt",
        "dev-requirements.txt",
        "app-requirements.txt",  # the reported failing case (prefixed name)
        "APP-REQUIREMENTS.TXT",
    ],
)
def test_requirements_detection_allows_prefix_and_suffix(filename: str) -> None:
    assert detect_format(filename) == ManifestUpload.Format.REQUIREMENTS


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        # pyproject.toml with prefix/suffix/case
        ("pyproject.toml", ManifestUpload.Format.PYPROJECT),
        ("backend-pyproject.toml", ManifestUpload.Format.PYPROJECT),
        ("pyproject-old.toml", ManifestUpload.Format.PYPROJECT),
        ("PYPROJECT.TOML", ManifestUpload.Format.PYPROJECT),
        # pixi.toml
        ("pixi.toml", ManifestUpload.Format.PIXI_TOML),
        ("pixi-dev.toml", ManifestUpload.Format.PIXI_TOML),
        ("app-pixi.toml", ManifestUpload.Format.PIXI_TOML),
        # pixi.lock
        ("pixi.lock", ManifestUpload.Format.PIXI_LOCK),
        ("pixi-prod.lock", ManifestUpload.Format.PIXI_LOCK),
        ("app-pixi.lock", ManifestUpload.Format.PIXI_LOCK),
        # environment.yml / .yaml
        ("environment.yml", ManifestUpload.Format.CONDA),
        ("environment.yaml", ManifestUpload.Format.CONDA),
        ("dev-environment.yml", ManifestUpload.Format.CONDA),
        ("environment-prod.yaml", ManifestUpload.Format.CONDA),
        ("ENVIRONMENT.YML", ManifestUpload.Format.CONDA),
    ],
)
def test_detection_allows_prefix_and_suffix_for_all_formats(filename: str, expected: str) -> None:
    assert detect_format(filename) == expected


@pytest.mark.parametrize(
    "filename",
    ["notes.txt", "readme.txt", "requirements.md", "Pipfile", "config.toml", "poetry.lock", "docker-compose.yml"],
)
def test_non_manifest_names_rejected(filename: str) -> None:
    with pytest.raises(UnsupportedFormatError):
        detect_format(filename)


@pytest.mark.django_db
def test_prefixed_requirements_upload_succeeds() -> None:
    response = _upload(_login(), "app-requirements.txt", b"django==5.2\n")
    assert response.status_code == 201
    assert response.data["detected_format"] == "requirements"


@pytest.mark.django_db
def test_upload_manifest_allows_no_user() -> None:
    from django.core.files.uploadedfile import SimpleUploadedFile

    from generate_sbom.manifests.services import upload_manifest

    user = register_user(email="alice@example.com", password="pw12345678")
    org = create_org(name=user.email.split("@")[0], admin_user=user)
    upload = upload_manifest(
        org,
        None,  # API-key upload: no user
        file_obj=SimpleUploadedFile("pixi.lock", b"version: 5\npackages: []\n"),
        application_id="A",
        component_name="c",
        repository_url="https://github.com/a/b",
        source_branch="main",
    )
    assert upload.user is None
    assert upload.detected_format == "pixi_lock"


@pytest.mark.django_db
def test_unsupported_format_rejected() -> None:
    response = _upload(_login(), "Pipfile", b"[packages]\n")
    assert response.status_code == 400
    assert response.data["code"] == "unsupported_format"


@pytest.mark.django_db
def test_malformed_toml_rejected() -> None:
    response = _upload(_login(), "pyproject.toml", b"not = = valid [[[ toml")
    assert response.status_code == 400
    assert response.data["code"] == "parse_error"


@pytest.mark.django_db
def test_non_utf8_rejected() -> None:
    response = _upload(_login(), "requirements.txt", b"\xff\xfe\x00bad")
    assert response.status_code == 400
    assert response.data["code"] == "parse_error"


@pytest.mark.django_db
def test_missing_metadata_rejected() -> None:
    client = _login()
    file = SimpleUploadedFile("requirements.txt", b"django==5.2\n")
    response = client.post(
        "/api/v1/manifests/upload/",
        {"file": file, "application_id": "A"},
        format="multipart",
    )
    assert response.status_code == 400
    assert response.data["code"] == "validation_error"


@pytest.mark.django_db
def test_invalid_repo_url_rejected() -> None:
    response = _upload(_login(), "requirements.txt", b"django==5.2\n", repository_url="not-a-url")
    assert response.status_code == 400
    assert response.data["code"] == "validation_error"


@pytest.mark.django_db
def test_manifest_format_override_is_honored() -> None:
    response = _upload(_login(), "deps.txt", b"django==5.2\n", manifest_format="requirements")
    assert response.status_code == 201
    assert response.data["detected_format"] == "requirements"


@pytest.mark.django_db
def test_path_traversal_filename_is_sanitized() -> None:
    response = _upload(_login(), "../../etc/requirements.txt", b"django==5.2\n")

    assert response.status_code == 201
    upload = ManifestUpload.objects.get(pk=response.data["upload_id"])
    assert upload.original_filename == "requirements.txt"
    assert ".." not in upload.file.name


@pytest.mark.django_db
def test_upload_requires_authentication() -> None:
    file = SimpleUploadedFile("requirements.txt", b"django==5.2\n")
    response = APIClient().post(
        "/api/v1/manifests/upload/",
        {"file": file, **META},
        format="multipart",
    )
    assert response.status_code in (401, 403)
