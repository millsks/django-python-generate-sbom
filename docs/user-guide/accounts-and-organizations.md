# Organizations

Every job, SBOM, and API key belongs to an **organization** — a line of business, not a
permission boundary between people.

!!! warning "This application does not require you to sign in"

    There is no login, no registration, and no password. Every page and every API endpoint
    is open to anyone who can reach the server.

    This is deliberate and temporary. Identity will be supplied by the platform the app is
    hosted on, through single sign-on and group membership. Until that lands, **deploy this
    application only on a network where every user is already trusted.**

## Where organizations come from

Organizations are **seeded from a committed file**, `orgs.yml`, rather than created in the
app. They are lines of business known in advance, so listing them in a file that goes
through review avoids the typos, near-duplicates, and accidental variants that a
free-text form collects.

To add one, add it to `orgs.yml` and run `pixi run seed-orgs`. The command is safe to run
repeatedly: it creates what is missing and leaves everything else alone. Removing a line
does **not** delete an organization — that would orphan its jobs and artifacts, which is a
deliberate act rather than a side effect of editing a file.

The system **Admin** organization is an internal tier, not somewhere work is filed. It is
never offered as a workspace.

## Choosing the organization for a job

You choose it **on the upload form**, using the **Organization** field, at the moment you
submit. That is the only place it is chosen, and the choice is permanent for that job: it
is recorded on the job and written into the generated SBOM as the document's **supplier**,
so the artifact itself says which line of business it describes.

!!! note "There is no organization switcher"
    There used to be one in the header. It selected a mode for the whole interface, and
    with sign-in removed it accepted any organization from anyone — so it was a filter
    wearing a permission's clothes. The organization is now a property of each job rather
    than a state the interface sits in.

## Seeing work across organizations

**Job Status lists every organization's jobs**, with an **Organization** column and a
filter beside Status and Manifest format. Filter to one organization to narrow the list.

Because there is no sign-in, this is not a change in who can see what: anyone could
already reach any organization's jobs through the old switcher. The list simply says so
plainly, and it means a job you file against one organization is still visible after you
submit it.

!!! danger "Delete all artifacts follows the filters"
    The **Delete all artifacts** button on Job Status acts on whatever the table is
    currently showing. Filtered to one organization, it is confined to that organization;
    with the filters cleared it really does mean every job in every organization — which is
    what the confirmation says. Job records and their metadata are always kept; only the
    downloadable files are removed.

!!! info "Screenshots"
    Not captured. See the note in the [User Guide index](index.md).
