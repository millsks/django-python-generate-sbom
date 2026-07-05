# Accounts & Organizations

Most work in the app belongs to an **organization**. Your jobs, SBOMs, API keys, and
fellow members are all scoped to the organization you are currently acting in. A new
account starts with **no** organization — you create one or ask an admin to add you
before there is anything to act in.

## Register

1. Open the app and choose **Register** in the top navigation.
2. Provide your account details and submit.
3. Registration creates your user account only — no organization is created for you.
4. You are then sent to the login page automatically. If you would rather not wait, use
   the **Go to login now** link on the confirmation message.

## Log in

1. Choose **Login** in the top navigation.
2. Enter your credentials and submit.
3. On success you are taken to the page you were trying to reach (or the dashboard if you
   went straight to the login page).

!!! tip "Protected pages remember where you were going"
    If you open a page that requires signing in (for example a results link someone
    shared), you are sent to the login page first and then returned to that original page
    once you sign in.

## No organization yet

Because registration no longer creates an organization for you, the first time you sign
in you have none. On the organization-scoped pages you see an empty state that reads:

> You're not in an organization yet — create one or ask an admin to add you.

You have two ways forward:

- **Create your own organization** (see below), or
- **Ask an existing organization's admin to add you** using the email address you
  registered with. Once they add you, the organization appears in your switcher.

## Create an organization

You can create an organization at any time — whether it is your first or an additional
one:

1. Open the **organization switcher** in the top bar and choose **New organization**. If
   you have no organizations yet, this appears as a **Create organization** button
   instead (the same button also appears on the "no organization yet" empty state).
2. Enter a name in the **Create an organization** dialog and choose **Create**.
3. You become the organization's admin, and the app switches you into it right away.

## Switch organizations

If you belong to more than one organization, use the **organization switcher** in the top
bar to change which one you are acting in. The active organization determines which jobs,
SBOMs, and API keys you see. Switching takes effect immediately across the app.

## Members (admins)

Organization admins see a **Members** link in the navigation. From there an admin can add
people to the organization, remove them, and hand over the admin role. Non-admins do not
see this link. See [Invite a member / switch organizations](../how-to/manage-organization.md)
for the details.

## Platform administrators

Platform (global) administrators belong to a system-wide **Admin** organization and
oversee every organization in the app. A global admin is automatically an admin of all
organizations — existing ones and any created later — so they can help manage membership
anywhere.

## Log out

Open the **account menu** in the top-right of the header and choose **Logout**. You are
returned to a public page and the navigation reverts to its signed-out state.

!!! info "Screenshots"
    _Screenshots of registration, login, and the organization switcher are added with the
    UI polish work._
