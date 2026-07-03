"""Tests for the structlog configuration (NFR-5.3)."""

import json

import pytest
import structlog

from generate_sbom.common.logging import configure_structlog


def test_json_renderer_emits_single_json_line(capsys: pytest.CaptureFixture[str]) -> None:
    """With json_logs=True, a log call emits one JSON line with bound fields."""
    configure_structlog(json_logs=True)
    structlog.get_logger().info("job_started", org_id="org-123", task_id="t-1")

    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert data["event"] == "job_started"
    assert data["org_id"] == "org-123"
    assert data["task_id"] == "t-1"


def test_console_renderer_emits_event(capsys: pytest.CaptureFixture[str]) -> None:
    """With json_logs=False, the console renderer still surfaces the event name."""
    configure_structlog(json_logs=False)
    structlog.get_logger().info("hello", key="val")

    assert "hello" in capsys.readouterr().out
