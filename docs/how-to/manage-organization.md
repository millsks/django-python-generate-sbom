# Invite a member / switch organizations

**Goal:** work across organizations and manage who belongs to them.

## Create or switch the active organization

1. Sign in. Your current organization is shown in the **organization switcher** in the
   header. If you belong to a single organization, the switcher shows its name as plain
   text (there is nothing to switch to).
2. To move between organizations, open the switcher and pick another one you belong to.
   The active organization changes; uploads, jobs, reports, and API keys all apply to
   whichever organization is active.
3. To start a **new** organization, choose **New organization** from the switcher (or the
   **Create organization** button), enter a name, and choose **Create**. You become its
   admin and are switched into it immediately.

!!! note "Only platform admins can create organizations"
    Creating an organization is restricted to **global admins** (platform admins), so the
    **New organization** / **Create organization** affordance appears for them only. If
    you are a regular member with no organization yet, ask a global admin or an existing
    org's admin to add you — you cannot create one yourself.

## Add and manage members (admins)

1. With the target organization active, go to **Members** (`/members`). This is available
   to organization **admins**.
2. Under **Add a member**, choose how to add the person:
     - **Add existing** — enter the **email address the person registered with** and
       choose **Add member**. This links an already-registered user to your organization.
     - **Create new user** — enter an email and a **temporary password** and choose
       **Create user**. This provisions a brand-new account and adds it to the
       organization in one step. Share the temporary password with the new member
       out of band; there is no automated email.
3. Manage existing members from the table's **Actions**:
     - **Remove** takes someone out of the organization.
     - **Make admin** promotes a member to the admin role.
     - **Make member** demotes an admin back to a member.

!!! warning "Add existing needs an existing account"
    **Add existing** only works for someone who has already created an account. If no
    account matches the email, the app shows **"No registered user with that email. Use
    'Create new user' to provision an account."** Either ask them to register first, or
    switch to **Create new user** to make the account for them.

!!! note "Every organization keeps at least one admin"
    You cannot remove or demote the organization's only admin, and the sole admin cannot
    leave. To step down, use **Make admin** to promote another member first, then demote
    or remove yourself. Global admins belong to **every** organization, so they cannot be
    removed or demoted from a single org — their status is managed from the Global Admins
    screen, not a single organization's Members page.

## Manage global admins (platform admins)

Global admins see a **Global Admins** link in the navigation. It opens a platform-admin
screen for the global-admin tier:

- **Grant global admin** by entering a registered user's email. If no user matches, the
  screen shows **"No registered user with that email."**
- **Revoke** a global admin. This removes them from the system **Admin** organization and
  demotes them to a member of every other organization. You cannot revoke the last
  remaining global admin — the app blocks it with **"There must always be at least one
  global admin."**

## Result

You can create organizations (as a global admin) and move between them from the header
and, as an admin, control membership and roles per organization. See also the
[User Guide](../user-guide/index.md).
