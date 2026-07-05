# Find outdated dependencies

**Goal:** see which installed packages are behind the latest release and which are on a
supported (LTS) line.

## Steps

1. Open a finished job's **Results** page and select the **Version Currency** tab.
2. Read each row:
    - **Package** — links to its registry page (PyPI project, or the conda-forge channel
      on prefix.dev).
    - **Installed** — the version from your manifest.
    - **Latest (PyPI)** — the latest release on PyPI.
    - **conda-forge Latest** — the latest on conda-forge (via prefix.dev); shown in an
      error color when it differs from the PyPI latest.
    - **Status** — `Current`, `Behind 1`, `Behind 2+`, or `Unknown`.
    - **LTS / On LTS** — the tracked long-term-support line and whether you are on it.
    - **Source** — whether the package resolves from PyPI or Conda.
3. Click the **Status** column header to sort by outdatedness and surface the
   `Behind 2+` packages first.
4. Bump the packages you want to update in your manifest, then re-run the job to confirm
   they move to `Current`.

## Result

You have a prioritized view of stale dependencies and their target versions. Use
[Export a report to Excel](export-to-excel.md) to capture the full table (the package
links are preserved in the spreadsheet). See also the
[User Guide](../user-guide/index.md).
