# AI-assisted development policy

**Purpose:** get the speed of AI coding tools without lowering the bar for safety, privacy or
quality, in a codebase that handles health data.
**Principle:** AI is a powerful pair programmer, not an author of record. *The human who opens
the PR owns every line.*

> This repository was itself built with an AI coding agent (Claude Code) working under this
> policy: agent rules in `AGENTS.md`, the same CI gates, and PRs/commits labelled. Several
> defects in this repo were caught *by the gates, not by the agent*. That is the point of
> the gates.

## 1. Approved tools

| Tool | Use | Conditions |
|---|---|---|
| Claude Code (CLI / IDE) | Agentic coding, refactoring, tests, docs | Enterprise/team plan with no training on our data; repository rules via `AGENTS.md`/`CLAUDE.md` |
| GitHub Copilot (Business/Enterprise) | Inline completion | Organisation-managed seats; public-code filter on |
| Chat assistants (enterprise tenant) | Design discussion, explaining code, drafting docs | Only the organisation's enterprise tenant; never personal accounts |

Anything else (new tools, browser extensions, MCP servers, plugins) needs approval from the
lead developer and security, because each one is a new data flow. Requests go through a PR to
this file.

## 2. Data that must never go into a prompt

Regardless of tool or plan:

- **Real patient or personal data** of any kind: names, identity codes, contact details,
  appointment details, free-text notes, screenshots or logs that contain them. Use the
  synthetic seed data instead.
- **Production data, exports or database dumps**, even "anonymised" ones (re-identification is
  easier than it looks).
- **Secrets:** keys, tokens, connection strings, `.env` contents, certificates.
- **Security-sensitive specifics** not yet fixed: exploit details, unpatched vulnerability
  reports, penetration-test findings.
- **Customer/contract information** and anything marked confidential.

When asking an AI about a production incident, reproduce it with synthetic data first.

## 3. What agents may and may not do in this repository

Agents read [`AGENTS.md`](../AGENTS.md) automatically. In short, they may write code, tests and docs within the
architecture rules. They must **never**: create or modify migrations without asking; disable,
skip or weaken tests or CI; log personal data; add dependencies without justification;
cross module boundaries; commit secrets; push to protected branches or merge their own work.

Agents run with the same local guardrails as people: pre-commit hooks (gitleaks, ruff,
import-linter, eslint/prettier). Human approval is required for shell commands outside the
project and for any outward-facing action (pushing, deploying, publishing).

## 4. Reviewing AI-generated code

The same CI gates apply to every change; there is no "AI lane". On top of that, reviewers
pay particular attention to what AI tends to get wrong:

| Risk | What to check |
|---|---|
| Plausible but wrong logic | Do the tests actually exercise the rule? Would they fail without the change? |
| Missing negative/security cases | Ownership, role checks, audit entries, 404-vs-403 |
| Silent scope creep | Changes outside the stated task; unrequested refactors |
| Invented APIs or outdated library usage | Run it. Version-specific behaviour (e.g. a library that changed between majors) |
| Weakened safety nets | `noqa`, `type: ignore`, skipped tests, loosened lint rules: each needs a written reason |
| New dependencies | Purpose, alternatives, licence, maintenance status |
| Privacy | PII in logs, fixtures, error messages, test names |

**Authors of AI-assisted PRs** must be able to explain every line in review. "The AI wrote
it" is not an answer.

## 5. Labelling AI-assisted work

- The PR template's **"AI assistance used?"** section is mandatory: tool(s), scope (what
  the AI produced vs. what the human changed), and two attestations (understood every line;
  no restricted data in prompts).
- Apply the `ai-assisted` label to such PRs. This feeds the metrics in
  [ai-metrics.md](ai-metrics.md); it is **not** used to judge individuals.
- Commits produced mainly by an agent carry a `Co-Authored-By:` trailer naming the tool.

## 6. Incidents

If restricted data was pasted into a prompt: stop, do not try to "undo" it in the tool, and
report it to the lead developer and the data protection officer the same day. The question
is how the process failed, not who to blame. Fix the process (tooling, training, guardrails).

## 7. Review of this policy

Owned by the lead developer, with security and the DPO. Reviewed quarterly and whenever a new
tool is requested.
