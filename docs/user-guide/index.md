# User Guide

This guide walks through using **django-python-generate-sbom** end to end — from
creating an account to generating a Software Bill of Materials (SBOM) and reading each
report.

## What the app does

You upload a Python dependency manifest (for example a `requirements.txt` or
`pyproject.toml`), and the app resolves the full transitive dependency set, generates a
standards-based SBOM (CycloneDX or SPDX), and enriches it with analysis:
**vulnerabilities**, **license compliance**, a **dependency graph**, and **version
currency** (how far behind the latest each package is). You can read every report in the
browser, export any of them to Excel, and download the SBOM document itself.

## How this guide is organized

| Step | Page |
|---|---|
| 1. Create an account and organization | [Accounts & Organizations](accounts-and-organizations.md) |
| 2. Upload a manifest and start a job | [Generating an SBOM](generating-an-sbom.md) |
| 3. Read the results | [Reading the Results](reading-the-results.md) |
| 4. Export reports and download the SBOM | [Exporting & Downloading](exporting-and-downloading.md) |
| 5. Review past jobs | [Job History](job-history.md) |
| 6. Automate with API keys | [API Keys](api-keys.md) |

!!! info "Screenshots"
    Annotated screenshots are added alongside the UI polish work — this guide currently
    describes each screen in text.
