# Interpret the vulnerability report

**Goal:** understand which dependencies have known vulnerabilities and decide what to
fix first.

## Steps

1. Open a finished job's **Results** page and select the **Vulnerabilities** tab.
2. Read each row, which represents one advisory affecting an installed package:
    - **Package / Installed** — the affected dependency and the version in your manifest.
    - **CVE / GHSA** — the advisory identifiers (aliases are shown together).
    - **CVSS** — the numeric severity score, when published.
    - **Severity** — the qualitative rating (e.g. Critical, High, Medium, Low).
    - **CWE** — the weakness category.
    - **Advisory URL** — the upstream advisory to read the details and fixed versions.
3. Prioritize: sort or scan by **Severity** / **CVSS**, starting with Critical and High.
4. For each item worth acting on, open the **Advisory URL** to find the fixed version,
   then bump the dependency in your manifest and re-run the job.

## Result

You have a prioritized list of vulnerable packages and the versions that resolve them.
To share the full list, [export the report to Excel](export-to-excel.md). To confirm a
fix, [generate a new SBOM](generate-sbom.md) after updating your manifest. See also the
[User Guide](../user-guide/index.md).
