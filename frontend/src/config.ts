// Story 12.6: the product name — the single source for the browser document title
// (frontend/index.html) and the header brand, so the name isn't duplicated as a string.
export const APP_NAME = 'Generate SBOM'

// Story 11.8: outbound links surfaced in the app header (GitHub repo + docs site).
// Overridable at build time via Vite env vars (VITE_REPO_URL / VITE_DOCS_URL), with
// sensible defaults so the links work out of the box.
export const REPO_URL: string =
  import.meta.env.VITE_REPO_URL ?? 'https://github.com/millsks/django-python-generate-sbom'

export const DOCS_URL: string =
  import.meta.env.VITE_DOCS_URL ?? 'https://millsks.github.io/django-python-generate-sbom/'
