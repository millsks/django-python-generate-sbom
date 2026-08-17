# Vendored front-end assets

These files are third-party releases committed into the repository on purpose (Story 21.3).

**Why vendored and not loaded from a CDN:** Story 21.3 AC #3 forbids any external asset
reference, matching the precedent already set by `drf-spectacular-sidecar` (the OpenAPI UI
is self-hosted so the API docs work without internet access). The app has to run in
air-gapped and OpenShift environments (Epic 19). Story 21.19 removes Node and the npm
toolchain entirely, so npm cannot be the delivery path either.

| Asset | Version | Licence | Upstream |
|---|---|---|---|
| `css/bootstrap.min.css` | 5.3.8 | MIT | <https://github.com/twbs/bootstrap> |
| `js/bootstrap.bundle.min.js` | 5.3.8 | MIT | <https://github.com/twbs/bootstrap> |
| `js/htmx.min.js` | 2.0.8 | BSD-2-Clause (Zero-Clause variant) | <https://github.com/bigskysoftware/htmx> |
| `images/icons.svg` | Bootstrap Icons 1.13.1 | MIT | <https://github.com/twbs/icons> |

Bootstrap's own copyright banner is preserved at the top of both minified files. The icon
sprite carries its attribution in an XML comment.

## The icon sprite

`images/icons.svg` is **not** the upstream distribution. Bootstrap Icons ships ~2000 icons
as a webfont plus CSS (~200 KB). The product owner chose to vendor only the icons this UI
actually uses, assembled as an SVG sprite of `<symbol>` elements (~12 KB): no webfont to
download, no flash of unstyled text, and each icon is reviewable in the diff.

Reference one as:

```html
<svg class="bi" aria-hidden="true"><use href="{% static 'images/icons.svg' %}#bi-house-door"/></svg>
```

To add an icon, take the `<path>` data from the upstream icon of the same name and add a
matching `<symbol>`, keeping its `viewBox`. Do not hand-draw substitutes — the sprite must
stay a faithful subset so it can be re-derived from upstream.

## Upgrading

Replace the file, update the version in the table above, and re-run `pixi run ci`. For the
sprite, re-derive the symbols from the new release rather than editing paths in place.
