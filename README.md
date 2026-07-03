# django-python-generate-sbom

A self-hosted, open-source Django web service that accepts Python dependency
manifests and generates production-grade Software Bills of Materials (SBOMs) in
standard formats (CycloneDX, SPDX), alongside four analysis reports:
vulnerability findings, license obligations, dependency graph, and version
currency — through both a web UI and a REST API.

<!-- Badges: CI status, coverage, and PyPI version are added once the project publishes. -->

## Architecture

A modular Django monolith (`backend/`) with a Celery async pipeline, fronted by a
React SPA (`frontend/`). **Pixi is the umbrella toolchain for the whole project**:
a single root `pixi.toml` installs both the Python environment and the Node
runtime, and orchestrates every task.

```
django-python-generate-sbom/   ← project root (pixi umbrella)
  pixi.toml                     # Python env + Node runtime + all tasks
  backend/                      # Django + Celery
  frontend/                     # React + Vite (added in a later story)
  docker-compose.yml            # full local stack (added in a later story)
```

## Installation

Requires [pixi](https://pixi.sh). Node.js and Python are installed by pixi — no
separate toolchain setup needed.

```sh
pixi install          # installs Python + Node environments
pixi run bootstrap    # installs the pre-commit git hooks
```

## Quick start

```sh
pixi run test         # backend unit tests
pixi run ci           # full validation gate (build · type-check · lint · coverage)
```

Django management commands run inside the pixi environment:

```sh
pixi run python backend/manage.py migrate
```

## Development

All tasks run from the project root via `pixi run <task>`:

| Task | Purpose |
|---|---|
| `fmt` | Format the backend (`ruff format`) |
| `lint` | Lint the backend (`ruff check`) |
| `check` | Type-check the backend (`mypy`, strict) |
| `test` | Backend unit tests |
| `test-integration` | Backend integration tests |
| `cov` | Full test suite with the 90% coverage gate |
| `build` | Build the backend package distribution |
| `ci` | Full validation sequence (the merge gate) |

`pixi run ci` must exit 0 before any change is considered done.

## License

Licensed under the [Apache License 2.0](LICENSE).
