# Engineering standards

How we build CareSlot. These standards apply equally to code written by people and by AI
agents. Agents get the condensed, rule-shaped version in [AGENTS.md](../AGENTS.md).

## 1. Branching and commits

- **Trunk-based:** short-lived branches from `main` (`feat/…`, `fix/…`, `chore/…`), merged
  within a day or two. `main` is always releasable and protected: PR + green CI + one approval
  (two for paths in CODEOWNERS that touch crypto, auth, audit or migrations).
- **Conventional commits:** `type(scope): summary`, e.g. `feat(scheduling): …`,
  `fix(auth): …`, `test(contract): …`. The body explains *why*. If the change was found or fixed
  because a tool or test caught something, say so. That is how the team learns.
- **One concern per commit.** Bug fixes found along the way get their own commit, so they can be
  reviewed, reverted and cited on their own.

## 2. Definition of done

A change is done when **all** of these are true:

- [ ] Behaviour is covered by tests that fail without the change; security rules have
      **negative** tests (prove the forbidden thing is forbidden).
- [ ] `make check` passes locally; CI is green (lint, types, unit, integration, contract,
      E2E where relevant, dependency audit, secret scan, container scan).
- [ ] Every new read or write of patient data is audited, with a purpose.
- [ ] No personal data in logs, errors, fixtures, prompts or commit messages.
- [ ] API changes are reflected in `api/openapi.json` (`make openapi`) and are backwards
      compatible within `/api/v1`.
- [ ] Migrations are reversible and safe for a rolling deploy (expand → migrate → contract).
- [ ] UI changes are keyboard-accessible, labelled, use design tokens, and pass axe.
- [ ] Docs and ADRs are updated if a decision changed.

## 3. Test pyramid: what each level is for

| Level | Where | What it proves | Speed |
|---|---|---|---|
| **Unit** | `backend/tests/unit`, `frontend/src/**/*.test.ts(x)` | Business rules and authorisation in pure code, with in-memory fakes for ports. Most tests live here. | ms |
| **Integration** | `backend/tests/integration` | Real PostgreSQL via Testcontainers, built by the **real migrations**: constraints, triggers, locks, encryption at rest, the HTTP stack. | seconds |
| **Contract** | `backend/tests/contract` | The API matches its OpenAPI contract for generated inputs: no 5xx, documented statuses, content types and schemas. | ~40 s |
| **E2E** | `frontend/e2e` | A few critical journeys in a real browser against the real stack, with axe accessibility scans and security-header checks. | ~10 s per journey |

Rules of thumb:

- Push each test **as low as it can go** while still proving the point. A business rule
  belongs in a unit test; "two transactions cannot both book" can only be proven against a
  real database.
- **No SQLite in tests.** The partial index, trigger and advisory lock are PostgreSQL features.
- E2E tests are few, deterministic and **independent of starting state**. They clean up after
  themselves and run serially because they share demo users.
- A flaky test is a bug. Reproduce it, find the cause, fix it. Do not retry it into green.

## 4. Code review culture

Reviews exist to share knowledge and catch what tools cannot. They are not a gate to be
cleared or a stage for showing off.

- **Constructive and specific.** Point at the line, explain the risk, propose an alternative.
  Say "this lets a clinician without a care relationship read X; could we check Y first?",
  not "this is wrong".
- **Label the weight** of each comment: `blocking:`, `suggestion:`, `question:`, `nit:`.
  Nits never block.
- **Time-boxed.** First response within one working day. Keep PRs small (aim for under 400
  changed lines); a large PR is split, not "reviewed later". If a discussion runs past two
  rounds, talk.
- **Automate the boring parts.** Formatting, import order, Tailwind class order, boundaries,
  types and secrets are handled by tools (pre-commit + CI). Humans review design, security,
  data protection, naming and tests.
- **Same bar for AI-assisted code.** The author owns every line, whether they typed it or not,
  and must be able to explain it ([AI development policy](ai-development-policy.md)).
- **Praise good work** in reviews too, specifically. It teaches as much as criticism does.

## 5. Coding conventions (summary)

- **Python:** 3.12, `mypy --strict`, Ruff (lint + format). Timezone-aware UTC datetimes only.
  Pure-Python domain; Pydantic at the API edge; comments explain *why*.
- **Module boundaries:** see ADR-0001. Enforced by import-linter; never bypass, raise it instead.
- **TypeScript:** strict mode plus `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`;
  React Query for server state; generated API types only.
- **Tailwind:** semantic tokens (`bg-surface`, `text-ink`, `bg-brand`…), never raw colours or
  arbitrary values in components; compose with `cn()`; variants in `cva`; prefer native
  elements and state variants (`has-checked:`, `aria-checked:`) over JS-managed state classes.
  If you change a colour token, re-check contrast (WCAG 2.2 AA, 4.5:1 for text).
- **Errors:** raise `DomainError` subclasses; the edge turns them into problem+json.

## 6. Security and privacy habits

- Synthetic data only. Identity codes use the 900–999 range, which is never issued to real
  people. The domain rejects other ranges outside production.
- Secrets come from the environment / secret store. `make env` generates local keys;
  gitleaks runs in pre-commit and CI.
- New dependencies need a justification in the PR: purpose, alternatives, licence, maintenance.
  Dependabot proposes updates weekly; deliberate pins are documented in `dependabot.yml`.

## 7. Running the gates locally

```bash
make check                 # lint, types, all backend tests
make e2e                   # Playwright against `make up`
cd backend && uv run pre-commit run --all-files
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:0.58.1 \
  image --severity HIGH,CRITICAL --ignore-unfixed careslot-api   # same scan as CI
```
