"""DRF response serializers for analysis reports (schema documentation; Story 11.19).

These describe the inline JSON envelopes the report views return so the generated
OpenAPI schema exposes accurate response shapes. They are never used to serialize
instances — the views build the payloads directly — so they carry no behavior.
"""

from __future__ import annotations

from typing import Any

from rest_framework import serializers


class GraphReportResponseSerializer(serializers.Serializer[dict[str, Any]]):
    """The dependency-graph payload: Cytoscape ``{nodes, edges}`` lists (AD-9)."""

    nodes = serializers.JSONField()
    edges = serializers.JSONField()
