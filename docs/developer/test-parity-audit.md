# Test-Parity Audit — Epic 21

Story 21.19 deleted **39 vitest files (223 test cases, 3,645 lines)** along with the React
SPA. Coverage percentage cannot detect what that removed: it measures the Python tree,
which grew. A behaviour previously covered by a vitest file and now covered by nothing
would still show a rising number.

So this page maps every deleted test file to the Django test that covers the same
behaviour, or states plainly that the behaviour no longer exists. It is the acceptance
evidence for Story 21.23 AC #1, and the reason the merge is defensible rather than merely
green.

## Summary

| | |
|---|---|
| Deleted vitest files | 39 |
| Deleted test cases | 223 |
| Deleted lines | 3,645 |
| Python tests at closeout | 863 |
| Coverage | 96.7% against `--cov=src`, floor unchanged at 90% |
| Files mapped to a Django successor | 30 |
| Files whose behaviour no longer exists | 8 |
| Files revealing a **genuine gap** | 1 (see [Findings](#findings)) |

## Route guards and identity (5 files, 22 cases)

The SPA's guards described themselves as "UX, not the security boundary" — the API was
the boundary behind them. Server-rendered pages have no second line, so their successors
are the *actual* boundary and are tested harder than the originals were.

| Deleted | Cases | Successor |
|---|---|---|
| `auth/AuthProvider.test.tsx` | 6 | **No longer exists.** Client-side auth context is replaced by Django's session. Covered indirectly by `test_auth_pages.py` (25) |
| `components/ProtectedRoute.test.tsx` | 4 | `test_access_control.py` + `test_route_authorization_matrix.py` |
| `components/OrgRoute.test.tsx` | 4 | `test_access_control.py::OrgMemberRequiredMixin` cases + the matrix |
| `components/AdminRoute.test.tsx` | 4 | `test_access_control.py::OrgAdminRequiredMixin` cases + the matrix |
| `components/GlobalAdminRoute.test.tsx` | 4 | `test_access_control.py::GlobalAdminRequiredMixin` cases + the matrix |

`test_route_authorization_matrix.py` was **written for this audit** (57 cases). The Story
21.4 mixin tests use synthetic views, which proves the mixins are correct but not that
each real route is wired to the right one — a page that forgot its mixin entirely passed
every one of them. The matrix drives all ten real routes with six principals.

## Pages (11 files, 68 cases)

| Deleted | Cases | Successor |
|---|---|---|
| `pages/HomePage.test.tsx` | 5 | `test_landing_page.py` (16) |
| `pages/LoginPage.test.tsx` | 6 | `test_auth_pages.py` (25) |
| `pages/RegisterPage.test.tsx` | 4 | `test_auth_pages.py` |
| `pages/login-flow.test.tsx` | 2 | `test_auth_pages.py::test_login_returns_the_user_to_the_page_they_were_bounced_from` and `::test_a_new_user_sees_the_shared_no_org_state` — both original cases, including the Story 10.2 bounce-loop regression |
| `pages/OrganizationPage.test.tsx` | 4 | `test_org_pages.py` (35) |
| `pages/MembersPage.test.tsx` | 14 | `test_org_pages.py`, `test_membership.py` (32) |
| `pages/KeysPage.test.tsx` | 3 | `test_api_key_pages.py` (18) |
| `pages/UploadPage.test.tsx` | 5 | `test_upload_page.py` (16) |
| `pages/HistoryPage.test.tsx` | 15 | `test_history_page.py` (31), `test_jobs_list.py` (16) |
| `pages/ResultsPage.test.tsx` | 3 | `test_results_page.py` (26) |
| `pages/GlobalAdminsPage.test.tsx` | 7 | `test_global_admin_pages.py` (22) |

## Report tabs (6 files, 46 cases)

| Deleted | Cases | Successor |
|---|---|---|
| `components/OverviewTab.test.tsx` | 8 | `test_results_page.py` |
| `components/SbomTab.test.tsx` | 12 | `test_sbom_tab.py` (16) |
| `components/VulnerabilitiesTab.test.tsx` | 5 | `test_vulnerabilities_tab.py` (21) |
| `components/LicensesTab.test.tsx` | 11 | `test_licenses_tab.py` (15) |
| `components/VersionsTab.test.tsx` | 8 | `test_versions_tab.py` (17) |
| `components/TabFailureNotice.test.tsx` | 2 | `test_vulnerabilities_tab.py` + `test_licenses_tab.py` (the shared partial is asserted from both) |

Every tab gained cases rather than losing them. The severity and currency **rank**
orderings — the defect magnets — are asserted as exact rendered sequences, which the
originals did by comparing arrays in memory.

## Shell and chrome (6 files, 34 cases)

| Deleted | Cases | Successor |
|---|---|---|
| `components/Layout.test.tsx` | 18 | `test_ui_shell.py` (15), `test_landing_page.py` |
| `components/SideNav.test.tsx` | 7 | `test_ui_shell.py` (nav gating by role) |
| `components/OrgSwitcher.test.tsx` | 6 | `test_org_switcher.py` (14) |
| `components/NoOrgState.test.tsx` | 3 | `test_access_control.py`, and the matrix asserts the state on **every** org-scoped route |
| `components/PageState.test.tsx` | 3 | **No longer exists.** Loading/empty/error is server-rendered per page; the states are asserted in each page's own module |
| `components/CreateOrgDialog.test.tsx` | 2 | `test_org_pages.py` |

## Ported helpers (8 files, 34 cases)

The Dev Notes flagged these as the place a dropped port would surface, since they cover
pure logic with no UI.

| Deleted | Cases | Successor | Ported? |
|---|---|---|---|
| `duration.test.ts` | 5 | `test_history_page.py` (parametrised over `format_duration`) | Yes — `tables.format_duration` cites `duration.ts` |
| `registryLinks.test.ts` | 6 | `test_versions_tab.py::test_registry_urls_are_encoded` + link assertions | Yes — including URL-encoding of names with spaces and slashes |
| `reportSheets.test.ts` | 7 | `test_excel_export.py` (29) | Yes — all four sheet builders |
| `excelExport.test.ts` | 4 | `test_excel_export.py` | Yes — plus a reference workbook generated from the real exceljs pipeline and compared cell for cell |
| `icons.test.ts` | 4 | `test_landing_page.py` (mapping completeness, no hardcoded sprite ids, unknown name raises) | Yes — `icons.ts` → `icons.py` |
| `favicon.test.ts` | 2 | `test_landing_page.py::test_the_favicon_is_carried_over` | Yes |
| `api/config.test.ts` | 1 | `test_app_config.py` (3) | Yes — the endpoint is unchanged and directly tested |
| `theme.test.ts` | 5 | — | **No — see Findings** |

## Hooks and API client (3 files, 12 cases)

| Deleted | Cases | Successor |
|---|---|---|
| `hooks/useJobStatus.test.ts` | 5 | `test_job_polling.py` (17) — polling moved to htmx against a server partial |
| `hooks/useDocumentTitle.test.ts` | 3 | `test_landing_page.py::test_inner_pages_keep_the_spa_title_form` |
| `api/orgs.test.ts` | 6 | `test_orgs.py` (6), `test_org_switcher.py` — the endpoints are unchanged; only the TypeScript client is gone |

`frontend/src/test/setup.ts` (2 lines) was vitest harness configuration, not a test.

## Findings

**One genuine gap, and it is a design decision rather than a missing test.**
`theme.test.ts` asserted Epic 12's brand palette: the red/gold primary/secondary in both
modes, error kept visually distinct from the brand primary, backgrounds and dividers
derived from a neutral ramp, and a reusable accent spectrum for data-viz. **None of that
was carried over.** The server-rendered UI uses Bootstrap's default palette —
`app.css` is deliberately thin and defines no brand colours — so there is no successor to
test, because there is nothing to assert.

This is not a regression in coverage; it is a change in the product's visual identity that
was never written down as such. It is recorded here so the product owner can accept it
explicitly during the Story 21.18 AC #5 walkthrough, or ask for the palette to be
re-introduced. Light/dark switching itself **is** covered, by
`test_ui_shell.py::test_theme_resolves_before_paint_from_the_shared_storage_key`.

Everything else either maps to a Django successor or covers a client-side mechanism that
no longer exists.
