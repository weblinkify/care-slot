# 0010. Use uv for Python dependency management

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
Reproducible builds need a lockfile with hashes. Day-one onboarding needs installs measured
in seconds, not minutes. CI caching should be simple.

## Decision
`uv` with `pyproject.toml` (PEP 621 + dependency groups) and a committed `uv.lock`.
CI and the Dockerfile install with `uv sync --frozen`: if the lockfile and pyproject disagree,
the build fails instead of silently resolving something new.

## Alternatives considered
- **pip + pip-tools:** proven, but slower and with more moving parts (compile step, separate
  dev files).
- **Poetry:** heavier, with its own non-standard metadata (historically).

## Consequences
- Very fast installs locally and in CI; a single tool for venv, lock and run.
- Platform-specific resolution works in one lockfile. Example: `cryptography` resolves to a
  patched version on Linux (everything deployed and audited), while Intel-macOS local
  development uses the last version with a wheel. `pip-audit` runs on Linux, i.e. on what
  ships.
- uv is younger than pip. It's backed by Astral and widely adopted; reassess yearly.
