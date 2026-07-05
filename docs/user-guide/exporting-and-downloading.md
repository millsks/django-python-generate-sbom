# Exporting & Downloading

Once a job has results you can take them out of the app in two ways: export the analysis
reports to **Excel**, or download the **SBOM document** itself.

## Export reports to Excel

Every report tab that shows a table offers an **Export to Excel** action, and the
**Overview** tab offers **Export all to Excel**.

- **Per-report export** — from the Vulnerabilities, Licenses, or Version Currency tab,
  export just that report as an `.xlsx` workbook.
- **Export all** — from the Overview tab, produce a single workbook with one sheet per
  report.

The spreadsheets mirror what you see on screen, including the columns for each report. In
the Version Currency sheet, the **package name stays clickable**, linking to the same
registry page as in the app.

!!! tip "Exports are generated in your browser"
    Excel files are built client-side and download immediately — nothing is stored on the
    server for the export.

## Download the SBOM document

The generated SBOM document (in the format you chose when starting the job — CycloneDX
JSON/XML or SPDX JSON) can be downloaded from the results. This is the machine-readable
artifact to hand to other tools or attach to a release.

!!! note "Download links are time-limited"
    SBOM downloads use short-lived signed links. If a link has expired, reload the results
    and request the download again.

!!! info "Screenshots"
    _Screenshots of the export actions are added with the UI polish work._
