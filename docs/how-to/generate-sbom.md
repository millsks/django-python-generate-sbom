# Generate an SBOM

**Goal:** produce a CycloneDX SBOM and its analysis reports from a Python dependency
manifest.

## Steps

1. Go to **Upload** (`/upload`). There is no sign-in.
2. Choose the **Organization** the job is filed against. It is recorded on the job and
   written into the SBOM as its supplier, so it cannot be changed afterwards.
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
5. Watch the task list on the **Results** page. Every pipeline task is listed; the ones
   running animate, and each shows `[COMPLETE]` or `[ERROR]` as it finishes. The bar at the
   bottom advances as tasks complete. The page moves to the full results by itself when the
   job is done.

## Result

The Results page opens with tabs for **Overview**, **Vulnerabilities**, **Licenses**,
**Version Currency**, and the raw **SBOM** document. From here you
can:

- [Interpret the vulnerability report](interpret-vulnerabilities.md)
- [Check license compliance](check-license-compliance.md)
- [Find outdated dependencies](find-outdated-dependencies.md)
- [Export a report to Excel](export-to-excel.md)

Jobs are always available under **Job Status** (`/job-status`). For the full walkthrough,
see the [User Guide](../user-guide/index.md).
