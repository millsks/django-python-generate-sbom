# API Keys

API keys let you call the app's REST API programmatically — for example to generate SBOMs
from CI. Keys are scoped to your **organization** and managed on the **API Keys** page (in
the top navigation).

## Create a key

1. Open **API Keys**.
2. Enter a descriptive **Key name** (so you can recognize it later) and choose **Create
   key**.
3. The full key is shown **once**, in a *"Copy your API key now"* dialog. Copy it
   immediately and store it somewhere safe.

!!! warning "The full key is shown only once"
    After you close the dialog, only the key's short **prefix** is ever displayed again.
    If you lose the key, revoke it and create a new one.

Each organization can hold up to **10** keys at a time.

## Use a key

Send the key in the `Authorization` header using the `Api-Key` scheme:

```http
Authorization: Api-Key <your-key>
```

For example:

```sh
curl -H "Authorization: Api-Key <your-key>" \
     https://your-host/api/...
```

The request acts as your organization. See the [API Reference](../api/index.md) and the
interactive Swagger UI (`/api/docs/`) for the available endpoints.

## Revoke a key

On the **API Keys** page, each key shows its name, prefix, and creation date. Choose
**Revoke** to disable a key immediately — any client still using it will start receiving
`401 Unauthorized`.

!!! info "Screenshots"
    _Screenshots of the API Keys page are added with the UI polish work._
