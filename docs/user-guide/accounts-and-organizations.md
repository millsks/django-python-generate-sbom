# Accounts & Organizations

Most work in the app belongs to an **organization**. Your jobs, SBOMs, API keys, and
fellow members are all scoped to the organization you are currently acting in. A new
account starts with **no** organization — an admin adds you (or, if you are a platform
admin, you create one) before there is anything to act in.

## Roles at a glance

The app has three role tiers:

| Role | What they can do |
|---|---|
| **Member** | Upload manifests, generate SBOMs, and read reports in the organizations they belong to. |
| **Organization admin** | Everything a member can, plus manage that organization's membership (add, remove, promote, and demote people) and its API keys. Admin of one organization does not grant admin of another. |
| **Global admin** | A platform-wide administrator. Global admins belong to a system **Admin** organization and are automatically an admin of **every** organization — existing and any created later. Only global admins can create organizations and manage the global-admin tier. |

## Register

1. Open the app and choose **Register** in the top navigation.
2. Provide your account details and submit.
3. Registration creates your user account only — no organization is created for you.
4. You are then sent to the login page automatically. If you would rather not wait, use
   the **Go to login now** link on the confirmation message.

## Log in

1. Choose **Login** in the top navigation.
2. Enter your credentials and submit.
3. On success you are taken to the page you were trying to reach (or the home page if you
   went straight to the login page).

!!! tip "Protected pages remember where you were going"
    If you open a page that requires signing in (for example a results link someone
    shared), you are sent to the login page first and then returned to that original page
    once you sign in.

## No organization yet

Because registration no longer creates an organization for you, the first time you sign
in you belong to none. Until you are in an organization you are **restricted to the home
page** — the organization-scoped destinations (Upload, History, API Keys) show a shared
empty state that reads:

> You're not in an organization yet — create one or ask an admin to add you.

For most users the way forward is to **ask an existing organization's admin to add you**
using the email address you registered with. Once they add you, the organization appears
and you can start working in it.

!!! note "Creating an organization is reserved for platform admins"
    Only **global admins** can create organizations (see below), so a **Create
    organization** button appears on that empty state only for them. A regular member
    simply waits to be added — there is no self-service org creation.

## Create an organization

Creating an organization is restricted to **global admins**. If you are a global admin,
you can create one at any time:

1. Open the **organization switcher** in the top bar and choose **New organization**. If
   you have no organizations yet, this appears as a **Create organization** button
   instead (the same button also appears on the "no organization yet" empty state).
2. Enter a name in the **Create an organization** dialog and choose **Create**.
3. You become the organization's admin, and the app switches you into it right away.

The system **Admin** organization is never shown in the switcher — it is an internal
platform-admin tier, not a workspace you act in.

## Switch organizations

If you belong to more than one organization, use the **organization switcher** in the top
bar to change which one you are acting in. The active organization determines which jobs,
SBOMs, and API keys you see. Switching takes effect immediately across the app.

!!! info "The switcher hides when you have a single organization"
    If you belong to exactly one organization there is nothing to switch to, so the
    switcher just shows the organization's name as plain text instead of a dropdown. Your
    active organization is also shown in the account menu and at the bottom of the side
    navigation.

## Members (admins)

Organization admins see a **Members** link in the navigation. From there an admin can add
people to the organization, remove them, and **promote** a member to admin or **demote**
an admin back to member. Non-admins do not see this link. See
[Invite a member / switch organizations](../how-to/manage-organization.md) for the
details.

## Platform administrators

Platform (**global**) administrators belong to a system-wide **Admin** organization and
oversee every organization in the app. A global admin is automatically an admin of all
organizations — existing ones and any created later — so they can help manage membership
anywhere, and they are the only role that can create organizations.

### Managing the global-admin tier

Global admins see a **Global Admins** link in the navigation (visible to global admins
only). It opens a management screen where a global admin can:

- **See the current global admins**, listed by email.
- **Grant global admin** to another user by entering their registered email. The person
  must already have an account; if no registered user matches, the screen shows
  **"No registered user with that email."**
- **Revoke** a global admin. Revoking removes them from the **Admin** organization and
  demotes them to a plain member of every other organization. As a safeguard, you cannot
  revoke the **last** remaining global admin — the app blocks it with
  **"There must always be at least one global admin."**

## Log out

Open the **account menu** in the top-right of the header and choose **Logout**. You are
returned to the login page and the navigation reverts to its signed-out state.

!!! info "Screenshots"
    _Screenshots of registration, login, the organization switcher, and the admin screens
    are added with the UI polish work._
