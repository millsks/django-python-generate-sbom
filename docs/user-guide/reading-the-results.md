# Reading the Results

The **Results** page shows one job's SBOM and analysis across a set of tabs.

While the job runs, the page lists **every task in the pipeline** instead of the tabs. The
tasks currently being worked on animate with a row of dots; each shows `[COMPLETE]` or
`[ERROR]` as it finishes, and the bar underneath advances as tasks complete. More than one
task can be running at once — the three analysis tasks run in parallel. The page moves to
the tabs by itself when the job is done; you do not need to reload it.

An `[ERROR]` beside one task does not stop the job: an analysis that cannot reach its data
source is reported as unavailable while everything else carries on.

The tabs, left to right, are: **Overview**, **SBOM**, **Vulnerabilities**, **Licenses**,
and **Version Currency**.

!!! note "A single report can fail without failing the whole job"
    Each analysis phase runs independently. If one phase fails (for example an external
    data source was unavailable), its tab shows a short failure notice while the other
    tabs still work.

## Overview

The **Overview** tab summarizes the job: headline counts (such as the total number of
packages) and the state of each report, with quick links to jump into the individual
tabs. It also offers **Export all to Excel**, which produces a single workbook containing
every report — see [Exporting & Downloading](exporting-and-downloading.md).

## SBOM

The **SBOM** tab shows the generated document in the browser: a **metadata block**
(component name, the tool, timestamp, and format) followed by the SBOM contents, so you
can inspect what was produced without downloading it. To save the file, use the download
action described in [Exporting & Downloading](exporting-and-downloading.md).

## Vulnerabilities

The **Vulnerabilities** tab lists known vulnerabilities affecting the resolved packages.
For each finding you see:

- the affected **package** and installed version,
- the advisory **IDs** (CVE / GHSA),
- the **CVSS** score and **severity**,
- associated **CWE**(s),
- a link to the **advisory**.

A summary breaks findings down by severity. The full report can be exported to Excel.

## Licenses

The **Licenses** tab groups packages by **legal-risk tier** — for example *Strong
Copyleft*, *Weak Copyleft*, and *Permissive* — so you can quickly see where the higher-risk
licenses are. Each entry shows the package, version, and detected license. Use
**expand/collapse all** to open or close every tier at once. The report can be exported to
Excel.

## Version Currency

The **Version Currency** tab shows how up to date each package is:

- **Installed** — the resolved version.
- **Latest (PyPI)** — the latest release on PyPI.
- **conda-forge Latest** — the latest version on conda-forge (via prefix.dev). When this
  differs from the PyPI latest it is highlighted, flagging that the two ecosystems are out
  of step.
- **Status** — a badge: *Current*, *Behind 1*, *Behind 2+*, or *Unknown*.
- **LTS** / **On LTS** — the tracked long-term-support series (when one applies) and
  whether the installed version is on it.
- **Source** — whether the package came from **PyPI** or **Conda**.

The **package name links to its registry page** (PyPI project page, or the conda-forge
channel on prefix.dev). By default the table is sorted by package name; click a column
header to sort by that column (for example **Status** to bring the most out-of-date
packages to the top). The report can be exported to Excel, with the package-name links
preserved in the spreadsheet.

!!! info "Screenshots"
    Not captured. See the note in the [User Guide index](index.md).
