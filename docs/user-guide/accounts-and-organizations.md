# Accounts & Organizations

Most work in the app belongs to an **organization**. Jobs, SBOMs, and API keys are all
scoped to the organization they were created in, and that separation still holds
completely — one organization's data is never visible from another.

!!! warning "This application does not require you to sign in"

    There is no login, no registration, and no password. Every page and every API endpoint
    is open to anyone who can reach the server, and every action — including creating
    organizations, managing members, and issuing API keys — is available to everyone.

    This is deliberate and temporary. Identity will be supplied by the platform the app is
    hosted on, through single sign-on and group membership. Until that lands, **deploy this
    application only on a network where every user is already trusted.**

## Organizations

An organization is a container for work, not a permission boundary between people. A
default organization is created when the database is first set up, and you can create
more at any time.

The organization you are "acting in" decides which jobs and keys you see, and which
organization a new upload is filed against. You choose it in two places: the
**organization switcher** in the header, and the **Organization** field on the upload
form.

## Create an organization

Open the **Organization** page from the navigation and create one by name. Creating an
organization used to be restricted to platform administrators; with sign-in removed it is
available to anyone.

The system **Admin** organization is never shown in the switcher and can never be selected
as a workspace — it is an internal tier, not somewhere work is filed.

## Switch organizations

Use the **organization switcher** in the header to change which organization you are
acting in. It determines which jobs, SBOMs, and API keys you see, and preselects the
**Organization** field when you upload. Switching takes effect immediately.

!!! info "The switcher hides when only one organization exists"
    With a single organization there is nothing to switch to, so the control is not
    rendered at all.

## Members

The **Members** page lists an organization's members and lets you add, remove, promote,
and demote them. Membership records still exist and are still editable, but they no longer
control access — anyone can reach any page. See
[Invite a member / switch organizations](../how-to/manage-organization.md) for the
details.

## Platform administrators

The **Admin** organization records a platform-administrator tier. Its members are
automatically an admin of every organization. The tier is still tracked and still
editable; like membership, it no longer gates anything.

### Managing the global-admin tier

The **Global Admins** page lets you:

- **See the current global admins**, listed by email.
- **Grant global admin** to another user by entering their registered email. The person
  must already have an account; if no registered user matches, the screen shows
  **"No registered user with that email."**
- **Revoke** a global admin. Revoking removes them from the **Admin** organization and
  demotes them to a plain member of every other organization. As a safeguard, you cannot
  revoke the **last** remaining global admin — the app blocks it with
  **"There must always be at least one global admin."**

!!! info "Screenshots"
    Not captured. See the note in the [User Guide index](index.md).
