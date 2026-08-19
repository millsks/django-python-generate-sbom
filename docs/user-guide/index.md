# User Guide

This guide walks through using **Python Inventory Supply Lens** end to end — from
choosing an organization to generating a Software Bill of Materials (SBOM) and reading
each report.

There is no account to create: the application has no sign-in. See
[Organizations](accounts-and-organizations.md) for what that means and why.

## What the app does

You upload a Python dependency manifest (for example a `requirements.txt` or
`pyproject.toml`), and the app resolves the full transitive dependency set, generates a
standards-based SBOM (CycloneDX or SPDX), and enriches it with analysis:
**vulnerabilities**, **license compliance**, and **version currency** (how far behind the
latest each package is). You can read every report in the
browser, export any of them to Excel, and download the SBOM document itself.

## How this guide is organized

| Step | Page |
|---|---|
| 1. Choose an organization | [Organizations](accounts-and-organizations.md) |
| 2. Upload a manifest and start a job | [Generating an SBOM](generating-an-sbom.md) |
| 3. Read the results | [Reading the Results](reading-the-results.md) |
| 4. Export reports and download the SBOM | [Exporting & Downloading](exporting-and-downloading.md) |
| 5. Track and review jobs | [Job Status](job-status.md) |
| 6. Automate with API keys | [API Keys](api-keys.md) |

!!! info "Screenshots"
    This guide describes each screen in text. Screenshots have not been captured; any
    added in future must be taken against the current server-rendered UI, not the
    retired React interface.
