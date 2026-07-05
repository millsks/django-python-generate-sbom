# Create and use an API key

**Goal:** call the REST API on behalf of your organization with a long-lived key instead
of a session.

## Create a key

1. Sign in with the target organization active.
2. Go to **API Keys** (`/keys`).
3. Create a new key and give it a recognizable name.
4. Copy the key value **immediately** — it is shown once and cannot be retrieved later.
   Store it somewhere safe (a secret manager, not source control).

!!! note
    An organization has a limit on the number of active keys. Delete keys you no longer
    use before creating new ones.

## Use a key

Send the key in the `Authorization` header with the `Api-Key` keyword. The API is served
under `/api/v1/`:

```sh
curl -H "Authorization: Api-Key <your-key>" \
  https://<your-host>/api/v1/sbom/jobs/
```

The key is scoped to the organization it was created in, so requests act on that org's
data.

## Result

You can automate SBOM generation and report retrieval without a browser session. Browse
the full set of endpoints and try them interactively in the built-in **Swagger UI** at
`/api/docs/` (also see the [API Reference](../api/index.md)). See also the
[User Guide](../user-guide/index.md).
