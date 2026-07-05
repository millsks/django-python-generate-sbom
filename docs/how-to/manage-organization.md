# Invite a member / switch organizations

**Goal:** work across organizations and manage who belongs to them.

## Create or switch the active organization

1. Sign in. Your current organization is shown in the **organization switcher** in the
   header. If you belong to no organizations yet, you see a **Create organization** button
   there instead.
2. To move between organizations, open the switcher and pick another one you belong to.
   The active organization changes; uploads, jobs, reports, and API keys all apply to
   whichever organization is active.
3. To start a new organization, choose **New organization** from the switcher (or the
   **Create organization** button), enter a name, and choose **Create**. You become its
   admin and are switched into it immediately.

## Add and manage members (admins)

1. With the target organization active, go to **Members** (`/members`). This is available
   to organization **admins**.
2. Under **Add a member**, enter the **email address the person registered with** and
   choose **Add member**. The person must already have an account — adding a member links
   an existing registered user to your organization.
3. Manage existing members from the table:
     - **Remove** takes someone out of the organization.
     - **Make admin** promotes a member to the admin role.

!!! warning "The person must already be registered"
    You can only add someone who has already created an account. If no account matches the
    email you enter, the app shows **"No registered user with that email."** Ask them to
    register first (with that email), then add them. There are no temporary passwords, and
    no account is created on their behalf.

!!! note "Every organization keeps at least one admin"
    You cannot remove the organization's only admin, and the sole admin cannot leave. To
    hand over ownership, use **Make admin** to promote another member first — if you were
    the only admin, you are stepped down to member automatically. (Platform admins belong
    to every organization and are managed separately, not from a single organization's
    Members page.)

## Result

You can create organizations and move between them from the header and, as an admin,
control membership and roles per organization. See also the
[User Guide](../user-guide/index.md).
