# Local containerless dev processes (Story 20.5) — run together with
# `pixi run dev` (honcho reads this file). Cross-platform: macOS and Windows.
# Each line delegates to a pixi task so cwd, per-OS pool overrides, and the
# local settings env are resolved by pixi (never gunicorn / sh -c here).
web: pixi run runserver
worker: pixi run worker
beat: pixi run beat
