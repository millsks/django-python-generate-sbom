# Job Status

The **Job Status** page (in the side navigation) lists SBOM jobs, most recent first —
both the ones still running and the ones already finished.

## What you see

For each job the list shows its key details and current **status** — for example queued,
running, completed, or failed. A job that is still running updates **live**, so you can
watch it progress without reloading the page. That is why the page is called Job Status
rather than History: it is as much about what is happening now as what happened earlier.

Each row also names the **organization** the job was filed against, and you can narrow the
list with the Organization, Status and Manifest format filters above the table.

## Open a job

Select a job to open its [Results](reading-the-results.md) page, where all of its report
tabs and downloads are available exactly as when it first completed.

!!! warning "Delete all artifacts follows the filters"
    The **Delete all artifacts** button acts on whatever the table is currently showing. Filter
    to one organization and it is confined to that organization; clear the filters and it
    really does mean every job in every organization — which is what the confirmation says.
    Job records and their metadata are always kept; only the downloadable files are removed.

!!! info "Screenshots"
    Not captured. See the note in the [User Guide index](index.md).
