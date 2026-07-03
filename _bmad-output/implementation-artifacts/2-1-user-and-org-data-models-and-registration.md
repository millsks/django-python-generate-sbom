# Story 2.1: User & Org Data Models + Registration

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a new user,
I want to register with my email and password,
so that I have an account with a personal org and can start submitting jobs.

## Acceptance Criteria

1. Given the registration page at `/register`, when I submit a valid email and password, then a `User` account is created, a personal `Org` is created (name derived from the email prefix), and an `OrgMembership` with `role="admin"` links the two.
2. Given the registration form, when I submit an email that is already registered, then I receive a validation error and no new account or org is created.
3. Given the `User`, `Org`, and `OrgMembership` models, when I inspect `OrgMembership.role`, then it accepts only `"admin"` or `"member"` — enforced at the model and serializer level.
4. Given `OrgMembership` and `Org` extend `OrgScopedModel` (where applicable), when `pixi run check` runs, then mypy (strict) passes on all three models with no errors.
5. Given unit tests covering the registration service function and all three models, when `pixi run cov` runs, then coverage on `users/` models and the registration logic is ≥90%.

## Tasks / Subtasks

- [ ] Task 1 — Extend the minimal `users.Org` model (AC: #1, #3, #4)
  - [ ] Story 1.3 already created a minimal `users.Org` (name, slug, created_at) to anchor `OrgScopedModel`'s FK. EXTEND it here — do NOT redefine or recreate it.
  - [ ] Confirm/add fields: `name` (display), `slug` (URL-safe, unique), `created_at`. Add slug auto-generation from name on create if not already present.
  - [ ] Do not add an `org` FK to `Org` itself (it is the tenant root, not org-scoped).
- [ ] Task 2 — `OrgMembership` model (AC: #1, #3, #4)
  - [ ] Fields: `org` FK(Org), `user` FK(settings.AUTH_USER_MODEL), `role` (choices: `admin` | `member`), `created_at`
  - [ ] `Meta.unique_together = (org, user)` — a user has at most one membership per org
  - [ ] Enforce `role` choices at the model level (`choices=`) AND in the serializer (AC #3)
  - [ ] Generate the migration
- [ ] Task 3 — Confirm the `User` model source (AC: #1)
  - [ ] Use the cookiecutter-django `users` custom User (email-based login) if present; otherwise use the project's custom user model. Do NOT introduce a second user model.
  - [ ] Ensure email is the unique login identifier (registration keys on email per AC #2)
- [ ] Task 4 — Registration service (AC: #1, #2)
  - [ ] `users/services.py`: `register_user(email: str, password: str) -> User` (or a dedicated `register` service) that, in a single transaction: creates the `User`, creates a personal `Org` (name derived from email prefix, unique slug), and creates an `OrgMembership(org, user, role="admin")`
  - [ ] Reuse/compose `create_org(name, admin_user)` from `users/services.py` (solution-design §3.1) for the org+admin-membership creation so the logic is shared with Story 2.3's create-org flow
  - [ ] Duplicate-email submission raises a validation error and creates nothing (transaction rolls back) (AC #2)
- [ ] Task 5 — Registration endpoint + form (AC: #1, #2)
  - [ ] `POST /api/v1/auth/register/` (unauthenticated) → creates org + admin user, returns the created user/org summary
  - [ ] Serializer validates email uniqueness and password; returns the standard error envelope `{"error": ..., "code": ...}` on failure
  - [ ] Registration page at `/register` (React) posts through `frontend/src/api/orgs.ts` (or a dedicated `auth.ts`) — no direct fetch in components (AD-5)
- [ ] Task 6 — Tests (AC: #4, #5)
  - [ ] Unit: `register_user` happy path creates User + Org + admin OrgMembership atomically
  - [ ] Unit: duplicate email → validation error, zero rows created (assert counts unchanged)
  - [ ] Unit: `OrgMembership.role` rejects a value outside {admin, member}
  - [ ] Unit: `unique_together(org, user)` prevents a duplicate membership
  - [ ] `pixi run check` (mypy strict) clean; `pixi run cov` ≥90% on `users/` models + registration

## Dev Notes

### Models (solution-design.md §3.1 — authoritative)

```python
class Org(models.Model):
    name: str          # display name
    slug: str          # URL-safe identifier, unique
    created_at: datetime

class OrgMembership(models.Model):
    org: FK(Org)
    user: FK(User)
    role: str          # 'admin' | 'member'
    # unique_together: (org, user)
```

`Org` is the tenant root — it is NOT org-scoped and does NOT extend `OrgScopedModel`. `OrgMembership` links users to orgs with a role. Neither of these needs an `org` FK beyond what's shown (`OrgMembership.org` is the link itself). Org-scoped feature models (`ManifestUpload`, `SBOMJob`) extend `OrgScopedModel` and point at this `Org` — that FK was already wired in Story 1.3.

### Critical: extend, do not redefine (dependency note)

Story 1.3 created a **minimal** `users.Org` (name, slug, created_at) purely to anchor `OrgScopedModel`'s FK target. This story EXTENDS that same model with slug generation and the membership relationship. Redefining `Org` would break the Story 1.3 migration and the `OrgScopedModel` FK. Add fields/behavior via a new migration; keep the model path `users.Org` stable.

### Services / selectors (solution-design.md §3.1)

```python
# users/services.py
def create_org(name: str, admin_user: User) -> Org: ...
# used by both registration (2.1) and create-additional-org (2.3)

# users/selectors.py
def get_org_members(org: Org) -> QuerySet[User]: ...
```

Follow the naming convention (spine Consistency Conventions): service functions `verb_noun(...)`, selectors `get_noun_by_x(...)`. Service functions accept/return plain Python objects only — no `HttpRequest`/`Response` (AD-3).

### GitHub-style org model (prd.md §Org and User Model)

- A user may belong to multiple orgs; orgs are fully isolated (Org A cannot see Org B's data — AD-2).
- Registration creates a **personal org** with the user as its sole admin.
- Additional orgs (Story 2.3) require the user to create them or be invited.

### Endpoint (solution-design.md §5.2)

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/register/` | No | Create org + admin user |

Error envelope on validation failure: `{"error": "<message>", "code": "<snake_case_code>"}` (spine Consistency Conventions).

### Testing standards

- Unit tests only for this story (no external I/O). Use Django's test DB.
- Registration must be transactional — test that a duplicate-email failure leaves zero new User/Org/OrgMembership rows.
- ≥90% coverage gate via `pixi run cov`; mypy strict via `pixi run check` (django-stubs configured in Story 1.1).
- Never `print()` / stdlib logging — structlog only; bind `user_id`/`org_id` on registration log events (NFR-5.3).

### Constraints / guardrails

- AD-1: `users/` is the base layer — it must not import from `manifests/`, `sbom/`, `analysis/`, or `tasks/`.
- File roles: `models.py` = ORM only; mutation logic in `services.py`; reads in `selectors.py`.
- Do not weaken the `OrgScopedModel` FK target or the Story 1.3 migration.

### Project Structure Notes

- All work lives under `backend/<project_slug>/users/` (models, services, selectors, serializers, views, urls).
- This is the first story to add real models to `users/` beyond the Story 1.3 minimal `Org`.
- Registration UI page `/register` lives in `frontend/src/pages/`; its API calls route through `frontend/src/api/`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1: User & Org Data Models + Registration]
- [Source: solution-design.md#3.1 users/]
- [Source: solution-design.md#5.2 Endpoint inventory]
- [Source: ARCHITECTURE-SPINE.md#AD-2 — OrgScopedModel]
- [Source: ARCHITECTURE-SPINE.md#AD-1 — Modular monolith]
- [Source: ARCHITECTURE-SPINE.md#Consistency Conventions — Module naming, File roles]
- [Source: prd.md#Org and User Model, FR-1.1]
- [Source: implementation-artifacts/1-3-core-shared-abstractions-and-django-configuration.md — minimal users.Org]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
