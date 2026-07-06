// Canonical manifest-format codes. The single source of truth is the backend
// ManifestUpload.Format enum (backend/generate_sbom/manifests/models.py); this list
// mirrors it in the exact same order. A backend test
// (backend/tests/unit/test_manifest_format_consistency.py) asserts the two match, so
// any drift — e.g. an Epic 8 rename/addition of a format — fails CI (Story 6.4, AC #4).
// The History-page format filter derives its options from this constant so the UI can
// never offer a value the backend rejects.
export const MANIFEST_FORMATS = ['requirements', 'pyproject', 'pixi_lock', 'pixi_toml', 'conda'] as const

export type ManifestFormat = (typeof MANIFEST_FORMATS)[number]
