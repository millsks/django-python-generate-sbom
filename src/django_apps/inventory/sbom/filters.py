"""django-filter filter sets for the server-rendered SBOM pages (Story 21.10)."""

from __future__ import annotations

import django_filters
from django.db.models import QuerySet

from inventory.manifests.models import ManifestUpload

from .models import SBOMJob
from .selectors import STATUS_FILTERS

#: "All" plus each status label the SPA offered. The labels — not the raw status codes — are
#: the querystring values, matching the existing API filter so a bookmarked URL keeps working.
STATUS_CHOICES = tuple((label, label) for label in STATUS_FILTERS)

#: Derived from the canonical backend enum, never hand-kept. HistoryPage.tsx carried the same
#: rule in a comment: "never a hand-kept list, so the dropdown can't offer a value the backend
#: rejects (Story 6.4, AC #4)".
FORMAT_CHOICES = ManifestUpload.Format.choices


class JobFilterSet(django_filters.FilterSet):
    """Status and manifest-format filters for the job history table."""

    status = django_filters.ChoiceFilter(
        choices=STATUS_CHOICES,
        method="filter_status",
        label="Status",
        empty_label="All",
    )
    format = django_filters.ChoiceFilter(
        choices=FORMAT_CHOICES,
        method="filter_format",
        label="Manifest format",
        empty_label="All",
    )

    class Meta:
        model = SBOMJob
        fields: tuple[str, ...] = ()

    def filter_status(self, queryset: QuerySet[SBOMJob], name: str, value: str) -> QuerySet[SBOMJob]:
        """Map a UI status label onto the underlying statuses (Story 6.1).

        The mapping is imported from the selectors module — the same one the API filter uses —
        so the two cannot disagree about what "In Progress" means.
        """
        statuses = STATUS_FILTERS.get(value)
        return queryset.filter(status__in=statuses) if statuses else queryset

    def filter_format(self, queryset: QuerySet[SBOMJob], name: str, value: str) -> QuerySet[SBOMJob]:
        """Filter on a canonical manifest-format code only (Story 6.4, AD-2).

        An unrecognised value yields an empty page rather than an error: Story 6.4 was a bug
        where a filter selection produced an error banner instead of rows.
        """
        if value not in ManifestUpload.Format.values:
            return queryset.none()
        return queryset.filter(manifest__detected_format=value)
