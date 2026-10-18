# AI risk register

**Scope:** every way AI touches CareSlot. That covers the AI coding agents that help build the
code (**live today**) and the planned AI day-summary assistant (**not built yet**: the controls
below are design requirements it must meet before it ships).
**Owner:** lead developer, with security and the data protection officer (DPO).
**Last reviewed:** 2026-10-18. Review it with the [AI policy](ai-development-policy.md) every
quarter, whenever a new AI tool, MCP server or plugin is requested, and before any AI feature
ships.

Rating: **L**ikelihood and **I**mpact are each Low / Medium / High, *after* the controls listed.
Each control names the file, gate or test that enforces it, so a reviewer can check it. A
control with no enforcement point is marked *process*. It depends on people following the
rule, so we watch it more closely.

---

## Part A: AI-assisted development (live)

AI agents (Claude Code, Copilot, chat assistants) write code, tests and docs in this
repository. The main risk is not that the AI is malicious. It is that it produces confident,
plausible output faster than people review it.

| ID | Risk | L | I | Controls | Enforced by |
|---|---|---|---|---|---|
| **D1** | **Personal data or secrets pasted into a prompt** leave our control (provider logs, retention, training) | L | H | Synthetic data only, so there is no real data to paste; approved tools only, on enterprise plans with no training on our data; a list of data that must never go into a prompt | [AI policy §1–2](ai-development-policy.md), `make seed`; *process* |
| **D2** | **Secret committed by an agent** (key in a fixture, `.env` added) | L | H | `make up` generates local keys into a git-ignored `.env`; test fixtures supply keys | pre-commit `gitleaks` + `detect-private-key`; CI gitleaks over full history |
| **D3** | **Plausible but wrong logic**, with tests that pass but do not test the rule | M | H | Every behaviour change ships with a test that would fail without it; the reviewer checks this specifically | [AGENTS.md §4](../AGENTS.md), PR template checklist, [AI policy §4](ai-development-policy.md) |
| **D4** | **Missing security cases**: no ownership check, 403 instead of 404, no audit entry | M | H | Negative tests are required for every security rule; audit runs in the same transaction as the access | `test_service.py`, `test_patients_and_audit.py`; CODEOWNERS on `shared/security.py` and `modules/audit/` |
| **D5** | **Safety nets weakened to get green CI**: skipped tests, `noqa`, `type: ignore`, loosened lint rules | M | H | Explicitly forbidden for agents; each suppression needs a written reason; CI config is reviewed like code | [AGENTS.md §6.2](../AGENTS.md); `mypy --strict`, ruff, ESLint in CI |
| **D6** | **Module boundaries eroded** by "convenient" cross-module imports or SQL | M | M | Modules talk only through their public interface or events | `lint-imports` (7 contracts) in pre-commit and CI |
| **D7** | **Hallucinated or typosquatted dependency**, or an outdated library API | M | H | A new dependency needs a written reason (purpose, alternatives, licence, maintenance); lockfiles are committed | PR template; `uv.lock` / `package-lock.json`; `pip-audit`, `npm audit`, Trivy, SBOM; Dependabot |
| **D8** | **Unreviewed schema change**: an agent writes an Alembic migration that drops or rewrites data | L | H | Agents must ask before touching migrations; migrations have a code owner | [AGENTS.md §6.1](../AGENTS.md); CODEOWNERS `/backend/migrations/` |
| **D9** | **Prompt injection through repository content.** Text in an issue, a dependency README, a web page or a tool result tells the agent to do something else | M | H | Agents treat fetched content as data, not instructions; shell commands outside the project and every outward action (push, deploy, publish) need a human; agents cannot merge their own PRs | [AI policy §3](ai-development-policy.md); branch protection; CODEOWNERS |
| **D10** | **Unvetted agent tooling** (MCP servers, plugins, browser extensions) opens a new data flow out of the repo | M | H | New tools need approval from the lead developer and security, through a PR to the AI policy | [AI policy §1](ai-development-policy.md); CODEOWNERS on the policy; *process* |
| **D11** | **Rules file tampered with.** A change to `AGENTS.md` or the AI policy quietly relaxes the rules for every later agent run | L | H | Both files have a code owner; a rule change is a reviewed PR like any other | CODEOWNERS `/AGENTS.md`, `/docs/ai-development-policy.md` |
| **D12** | **Scope creep and oversized PRs** that reviewers rubber-stamp | M | M | Small, focused changes; PR size tracked at team level | [AGENTS.md §7](../AGENTS.md); [ai-metrics.md](ai-metrics.md) |
| **D13** | **Over-reliance**: authors cannot explain the code they merge, and skills fade | M | M | "The AI wrote it" is not an answer in review; authors must be able to explain every line | [AI policy §4](ai-development-policy.md); *process* |
| **D14** | **Licence contamination** from verbatim reproduction of public code | L | M | Copilot public-code filter on; enterprise tools only | [AI policy §1](ai-development-policy.md); *process* |
| **D15** | **Metrics misused to judge individuals** cause people to hide AI use, which defeats labelling | L | M | Metrics are team-level only; the `ai-assisted` label is not used for performance review | [ai-metrics.md](ai-metrics.md), [AI policy §5](ai-development-policy.md) |

**What has gone wrong so far** (all caught by gates, not by the agent): a formatting slip, five
API contract gaps, a consent field that accepted non-booleans, 41 fixable CVEs in a base image,
nginx silently dropping every security header, and a duplicate connection pool that hid SQL
from traces. Each one became a regression test or a guardrail. The lesson for this register:
**gates, not agent self-review, are the control we rely on.**

---

## Part B: the AI day-summary assistant (planned)

**Intended feature:** a clinician gets a short, AI-written summary of the day's appointments.
It sits behind a feature flag, makes one LLM call per clinician per day, and does not run any
agent loop or tools. Nothing below is implemented yet. `modules/assistant` is an empty
placeholder. These are the **acceptance criteria**: the feature does not ship until each one
has its enforcement point and a test. ADR-0008 will record the design when it lands.

Risks are mapped to the [OWASP Top 10 for LLM Applications (2025)](https://genai.owasp.org/llm-top-10/).

| ID | Risk | OWASP | Required control | Required proof |
|---|---|---|---|---|
| **A1** | **Health data sent to the LLM provider** | LLM02 Sensitive information disclosure | The prompt is built only from a pseudonymised, minimised view: a per-request random alias instead of the patient id, slot time and appointment type from closed lists. No names, identity codes, contact details or free text, ever. Only patients with assistant consent are included | Unit test that serialises the prompt input and asserts that no field from `pat_*` and no free text is present; consent filter test |
| **A2** | **Re-identification** from the combination of fields (rare appointment type + exact time + small clinic) | LLM02 | Coarsen times to the hour; drop rare categories below a threshold; aliases are not stable across days | Test against the seed data that no record is unique on the fields sent |
| **A3** | **Prompt injection** through data that reaches the prompt | LLM01 Prompt injection | Closed lists only, so no user-controlled text reaches the prompt; the system prompt is fixed in code | Schema test: the prompt input model has no `str` fields without an enum or pattern |
| **A4** | **Harmful or wrong output** (invented appointments, clinical advice, a patient's name "guessed back") | LLM05 Improper output handling, LLM09 Misinformation | Output is validated against a strict schema (counts and alias references only); aliases are mapped back server-side; anything that does not validate is dropped and the plain list is shown; the UI labels it "AI-generated, check against the schedule" | Tests with malformed, oversized and injected model output |
| **A5** | **Output rendered unsafely** in the browser | LLM05 | Rendered as text through React escaping; no `dangerouslySetInnerHTML`; strict CSP is already in place | Existing `e2e/headers.spec.ts`; component test |
| **A6** | **Excessive agency**: the model triggers actions | LLM06 Excessive agency | No tools and no function calling. The model only returns text that is then validated. It cannot read, book, cancel or call anything | Code review; no tool definitions in the module |
| **A7** | **Unbounded cost or provider outage** | LLM10 Unbounded consumption | A per-day request cap; one cached summary per clinician per day; timeout and circuit breaker; the feature degrades to "no summary", never to a broken day view | Test for the cap and for the fallback ([NFRs §7](non-functional-requirements.md)) |
| **A8** | **Provider retains or trains on our data** | LLM02, LLM03 Supply chain | An enterprise contract with zero retention and no training; an EU data region; a data processing agreement signed before go-live; a DPIA updated by the DPO | Contract and DPIA on file; *process* |
| **A9** | **System prompt leaks** internal details | LLM07 System prompt leakage | The system prompt contains no secrets, ids or business rules that need protecting; authorisation never depends on the prompt | Code review |
| **A10** | **Access to AI output is not audited** | n/a (GDPR accountability) | Generating and viewing a summary writes an audit entry (actor, purpose, aliases → patient ids, server-side only) | Integration test in the audit chain |
| **A11** | **Model or provider change** silently changes behaviour | LLM03 Supply chain | Pinned model id; a provider change is a PR with re-run evaluation tests | Golden-output tests run against the mock and on demand against the real provider |
| **A12** | **Feature switched on before it is ready** | n/a | Feature flag off by default; on in production only after A1–A11 are green and the DPO signs off | Config test: default is off |

Not applicable by design: **LLM04 Data and model poisoning** and **LLM08 Vector and embedding
weaknesses**. We do not train or fine-tune, and we have no RAG or vector store. If either
changes, this register gets new rows first.

---

## Part C: agent-to-agent and future AI features

CareSlot has **no runtime agent-to-agent protocol** (see the README, *How agents work
together*). Any of the following needs a new ADR, rows in this register and a threat-model
entry *before* implementation:

- the assistant gaining tools, function calling or write access;
- RAG over any CareSlot data;
- a second model, or an agent delegating to another agent at runtime;
- any free text (notes, cancellation comments) reaching a model.

## Incidents

If personal data reaches an AI tool or provider, follow the [AI policy §6](ai-development-policy.md)
and [SECURITY.md](../SECURITY.md): stop, report it the same day to the lead developer and the
DPO, and assess whether the 72-hour GDPR breach notification applies. Fix the process. Do not
blame the person.
