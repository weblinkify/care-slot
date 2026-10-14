# AGENTS.md - rules for AI coding agents (and humans)

This file is the single source of truth for how code is written in CareSlot. AI agents
(Claude Code, Copilot, Cursor, ...) read it automatically; humans should read it once too -
the rules are the same for everyone. Background and rationale: `docs/engineering-standards.md`,
`docs/ai-development-policy.md`, `docs/adr/`.

## 1. What this system is

A modular monolith (FastAPI + PostgreSQL backend, React + Tailwind frontend) for booking
healthcare appointments and managing patient consent. **All data is synthetic.** Treat it as
if it were real patient data anyway - the habits are the point.

## 2. Architecture rules

- Backend modules live in `backend/src/careslot/modules/<module>/`:
  `scheduling`, `patients`, `consent`, `audit`, `assistant`.
- Each module has the same layers:
  - `domain/` - entities, value objects, domain events, business rules. Pure Python. No
    FastAPI, no SQLAlchemy, no I/O.
  - `application/` - use cases. Orchestrates domain + ports (repository interfaces).
  - `infrastructure/` - SQLAlchemy models and repositories, external adapters.
  - `api/` - FastAPI routers and request/response schemas. Thin: validate, call a use case,
    map the result.
  - `__init__.py` / `public.py` - the module's **public interface**. The only thing other
    modules may import.
- **Modules never import another module's internals and never query another module's
  tables.** Cross-module communication goes through the public interface or domain events
  on the event bus (`careslot.shared.events`). Enforced by `lint-imports` in CI.
- `careslot.shared` is a small shared kernel (config, db, errors, events, logging,
  security). It must not import from `modules`.
- `careslot.main` is the composition root: the only place that wires modules together.
- API is versioned under `/api/v1`. Errors are RFC 7807 problem details
  (`careslot.shared.errors`). Never return ad-hoc error shapes.

## 3. Coding conventions

- Python 3.12, type hints everywhere, `mypy --strict` clean, `ruff` clean.
- Datetimes are timezone-aware UTC (`datetime.now(UTC)`). Naive datetimes are rejected.
- Pydantic v2 models at the API edge; plain dataclasses in the domain.
- Explain *why*, not *what*, in comments - especially for security and design decisions.
- Frontend: strict TypeScript, React Query for server state, Tailwind with semantic tokens
  (`bg-surface`, `text-ink`, `bg-brand` ...). No raw hex colours or arbitrary values in
  components, compose classes with `cn()`, add variants with `cva`, reuse `components/ui/*`.
  Every interactive element must be keyboard accessible and labelled.

## 4. Testing expectations

- Every behaviour change ships with tests that would fail without the change.
- Unit tests for domain rules (`backend/tests/unit`), integration tests against real
  PostgreSQL via Testcontainers (`backend/tests/integration`), contract tests from the
  OpenAPI spec (`backend/tests/contract`), Playwright E2E for the booking flow
  (`frontend/e2e`).
- Security rules (ownership, roles, audit) need **negative** tests: prove the forbidden
  thing is forbidden.
- Run `make check` before opening a PR.

## 5. Security and privacy rules

- Every read or write of patient data writes an audit entry through the `audit` module.
- Never log personal data (names, identity codes, emails, phone numbers, free text). Log
  IDs. `shared.logging` redacts known keys as a safety net - do not rely on it.
- Sensitive columns are encrypted (`shared.crypto`). Keys come only from the environment /
  secret store. Never hard-code keys, even in tests (use the test fixtures).
- A patient may only access their own data. For someone else's record return **404, not
  403**, so the API does not confirm the record exists.
- The AI assistant only receives the pseudonymised, minimised view built in
  `modules/assistant`. Never pass identifiers or free text to an LLM provider.
- Validate all input at the API edge with Pydantic; constrain lengths and formats.

## 6. Things agents must NEVER do

1. Create, edit or delete Alembic migrations **without asking the human first.**
2. Disable, skip, delete or weaken tests or CI checks to make a build pass.
3. Log, print or include personal data in code, fixtures, prompts, commits or PR text.
4. Add a dependency without stating why in the PR (what it does, why stdlib/existing deps
   are not enough, its licence and maintenance status).
5. Bypass module boundaries (importing another module's internals, cross-module SQL).
6. Commit secrets, real keys or `.env` files.
7. Use real personal data, including "just for testing". Synthetic only.
8. Push directly to protected branches or merge their own PRs.

## 7. Workflow

- Small, focused changes. Conventional commits (`feat(scheduling): ...`).
- PRs use `.github/pull_request_template.md`, including the **AI assistance** section.
- If a rule here blocks you, stop and ask - do not work around it.
