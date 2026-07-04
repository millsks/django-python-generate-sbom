"""Tests for scheduled maintenance tasks (Story 8.10)."""

from unittest.mock import patch

from generate_sbom.tasks.maintenance import refresh_parselmouth_mapping


def test_refresh_task_delegates_to_parselmouth_service() -> None:
    with patch("generate_sbom.tasks.maintenance.parselmouth.refresh_mapping", return_value=42) as refresh:
        result = refresh_parselmouth_mapping.apply().get()

    refresh.assert_called_once()
    assert result == 42
