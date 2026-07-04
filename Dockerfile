# Single umbrella image for every Django/Celery service (AD-13).
#
# Installs the pixi environment (Python + Node), builds the React SPA into the
# image, and collects static assets. Each Compose service selects its process
# via `pixi run <task>` (web / worker-pipeline / worker-analysis / beat).
FROM ghcr.io/prefix-dev/pixi:0.72.0

WORKDIR /app

# Install the locked environment. The backend package is an editable install, so
# its source must be present before `pixi install`.
COPY pixi.toml pixi.lock ./
COPY backend/ backend/
RUN pixi install --locked
# Register Graphviz plugins for pygraphviz SVG rendering (the conda post-link
# script that does this is skipped without the local .pixi/config.toml, which the
# image doesn't carry).
RUN pixi run dot -c

# Build the SPA into frontend/dist, then collect static assets into STATIC_ROOT.
COPY frontend/ frontend/
RUN pixi run fe-build \
 && DJANGO_SETTINGS_MODULE=config.settings.production SECRET_KEY=build-only pixi run collectstatic

EXPOSE 8000

# Default process; Compose overrides per service.
CMD ["pixi", "run", "web"]
