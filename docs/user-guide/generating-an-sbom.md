# Generating an SBOM

Generating an SBOM starts from the **Upload** page (in the top navigation once you are
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

1. **Choose file** — select your manifest file.
2. **Application ID** — an identifier for the application this component belongs to.
3. **Component name** — the name of the component being described.
4. **Repository URL** — the source repository for the component.
5. **Source branch** — the branch the manifest was taken from.
6. **Output format** — the SBOM document format to produce (see below).

## Output formats

| Option | Description |
|---|---|
| **CycloneDX (JSON)** | CycloneDX in JSON — the default |
| **CycloneDX (XML)** | CycloneDX in XML |
| **SPDX (JSON)** | SPDX 2.3 in JSON |

## Start the job

Choose **Generate SBOM**. The app queues a job and takes you to its **Results** page,
where a progress bar tracks the pipeline as it resolves dependencies, builds the SBOM
document, and runs the analysis phases.

!!! info "One job at a time per organization"
    To keep resource use predictable, a new job waits if another is already running for
    your organization. You can watch progress on the Results page or from
    [Job History](job-history.md).

When the pipeline finishes, the Results page shows the report tabs — see
[Reading the Results](reading-the-results.md).

!!! info "Screenshots"
    _Screenshots of the upload form and the in-progress Results page are added with the UI
    polish work._
