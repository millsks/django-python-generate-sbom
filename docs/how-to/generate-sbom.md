# Generate an SBOM

**Goal:** produce a CycloneDX SBOM and its analysis reports from a Python dependency
manifest.

## Steps

1. Sign in and make sure the correct organization is active (see
   [Invite a member / switch organizations](manage-organization.md)).
2. Go to **Upload** (`/upload`).
3. Choose a supported manifest file. Supported formats:
    - `requirements.txt`
    - `pyproject.toml`
    - `pixi.lock`
    - `pixi.toml`
    - `environment.yml`

    The format is detected from the filename, so a prefixed/suffixed name such as
    `requirements-dev.txt` or `pixi-prod.lock` still works.
4. Submit the job. Only one job runs per organization at a time, so a new job may wait
   briefly if another is still running.
5. Watch the progress indicator. When the job finishes you are taken to the **Results**
   page (`/results/<task-id>`).

## Result

The Results page opens with tabs for **Overview**, **Vulnerabilities**, **Licenses**,
**Version Currency**, and the raw **SBOM** document. From here you
can:

- [Interpret the vulnerability report](interpret-vulnerabilities.md)
- [Check license compliance](check-license-compliance.md)
- [Find outdated dependencies](find-outdated-dependencies.md)
- [Export a report to Excel](export-to-excel.md)

Past jobs are always available under **History** (`/history`). For the full walkthrough,
see the [User Guide](../user-guide/index.md).
