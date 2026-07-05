# Reading the Results

The **Results** page shows one job's SBOM and analysis across a set of tabs. While the job
runs you see a progress bar; once it finishes the tabs populate.

The tabs, left to right, are: **Overview**, **SBOM**, **Vulnerabilities**, **Licenses**,
**Dependency Graph**, and **Version Currency**.

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

## Dependency Graph

The **Dependency Graph** tab visualizes the resolved dependencies as a graph, showing how
packages relate. **Direct** dependencies (declared in your manifest) are distinguished
from **transitive** ones (pulled in indirectly), so you can tell what your project asks
for versus what it inherits.

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
    _Screenshots of each tab are added with the UI polish work._
