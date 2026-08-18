# Single umbrella image for every Django/Celery service (AD-13).
#
# Installs the pixi environment (Python + Node), builds the React SPA into the
# image, and collects static assets. Each Compose service selects its process
# via `pixi run <task>` (web / worker-pipeline / worker-analysis / beat).
FROM ghcr.io/prefix-dev/pixi:0.72.0

WORKDIR /app

# Install the locked environment. The backend package is an editable install rooted at
# the repo root (Story 21.1), so BOTH pyproject.toml and the src/ tree it packages must
# be present before `pixi install` — an editable install cannot resolve a missing source.
COPY pixi.toml pixi.lock pyproject.toml manage.py ./
COPY src/ src/
RUN pixi install --locked

# Collect static assets into STATIC_ROOT. Story 21.19 removed the SPA build step that
# used to run first; the vendored assets now ship in the source tree copied above.
RUN DJANGO_SETTINGS_MODULE=config.settings.production SECRET_KEY=build-only pixi run collectstatic

EXPOSE 8000

# Default process; Compose overrides per service.
CMD ["pixi", "run", "web"]
