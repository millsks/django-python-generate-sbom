# Generating an SBOM

Generating an SBOM starts from the **Upload** page (in the side navigation once you are
signed in). You provide a dependency manifest and some metadata about the component, pick
an output format, and start the job.

## Supported manifest formats

The app detects and resolves these Python dependency manifests to their full transitive
package set:

| Format | Typical file |
|---|---|
| `requirements.txt` | pip requirements |
| `pyproject.toml` | PEP 621 / Poetry / uv project metadata |
| `pixi.toml` | Pixi project manifest |
| `pixi.lock` | Pixi lockfile (fully pinned) |
| `conda environment.yml` | Conda environment file |

!!! tip "Lockfiles give the most precise results"
    A fully resolved lockfile (such as `pixi.lock`) pins exact versions, so the SBOM and
    its analysis reflect exactly what would be installed. Looser manifests are resolved to
    a transitive set, which can vary as upstream releases change.

## Fill in the form

On the **Upload** page:

1. **Organization** — the line of business this job is filed against. This is the only
   place it is chosen, and the choice is permanent: it is recorded on the job, shown as a
   column on [Job Status](job-status.md), and written into the generated SBOM as the
   document's **supplier**. The options come from `orgs.yml` — see
   [Organizations](accounts-and-organizations.md).
2. **Manifest file** — select your manifest file.
3. **Application ID** — an identifier for the application this component belongs to.
4. **Component name** — the name of the component being described.
5. **Repository URL** — the source repository for the component.
6. **Source branch** — the branch the manifest was taken from.
7. **Output format** — the SBOM document format to produce (see below).

All fields are required. The provenance fields — Application ID, Component name,
Repository URL, Source branch, and the Organization — are embedded in the generated SBOM's
metadata, which is why the form asks for them rather than inferring them.

## Output formats

| Option | Description |
|---|---|
| **CycloneDX (JSON)** | CycloneDX in JSON — the default |
| **CycloneDX (XML)** | CycloneDX in XML |
| **SPDX (JSON)** | SPDX 2.3 in JSON |

## Start the job

Choose **Generate SBOM**. The app queues a job and takes you to its **Results** page,
which lists every task in the pipeline and marks each one complete as it finishes.

!!! info "One job at a time per organization"
    To keep resource use predictable, a new job waits if another is already running for
    your organization. You can watch progress on the Results page or from
    [Job Status](job-status.md).

When the pipeline finishes, the Results page shows the report tabs — see
[Reading the Results](reading-the-results.md).

!!! info "Screenshots"
    Not captured. See the note in the [User Guide index](index.md).
