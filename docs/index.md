# django-python-generate-sbom

Generate and analyze **CycloneDX SBOMs** for Python projects. Upload a manifest
(`requirements.txt`, `pyproject.toml`, or a lockfile), and the app resolves the
dependency tree and produces an SBOM plus enrichment reports:

- **Vulnerabilities** — known CVEs/GHSAs with severity and CVSS.
- **Licenses** — license compliance grouped by legal-risk tier.
- **Dependency graph** — direct vs. transitive relationships.
- **Version currency** — installed vs. latest (PyPI and conda-forge), with LTS tracking.

## Documentation

| Section | For |
|---|---|
| [User Guide](user-guide/index.md) | Using the app end to end |
| [How-To](how-to/index.md) | Quick, task-focused recipes |
| [Developer](developer/index.md) | Architecture, setup, and internals |
| [API Reference](api/index.md) | The REST API |
| [Contributing](contributing.md) | Working on the project |
