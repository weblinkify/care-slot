## What and why

<!-- What does this change do, and why is it needed? Link the issue. -->

## How it was tested

<!-- Which tests prove the change? Paste commands/output if useful. -->

## AI assistance used?

- [ ] No
- [ ] Yes. Tool(s): <!-- e.g. Claude Code, Copilot -->
  - Scope: <!-- e.g. "generated the repository class and tests; I rewrote the query" -->
  - [ ] I have read and understood every AI-generated line and can explain it in review
  - [ ] No personal, patient or confidential data was put into prompts (see docs/ai-development-policy.md)

## Reviewer checklist

- [ ] Tests prove the change (and would fail without it); security rules have negative tests
- [ ] No personal data in logs, errors, fixtures or commit messages
- [ ] Module boundaries respected (no cross-module internals or tables)
- [ ] Patient data access is audited and ownership-checked
- [ ] New dependencies justified (purpose, licence, maintenance)
- [ ] Migrations reviewed: reversible, safe for zero-downtime deploys
- [ ] API changes reflected in the OpenAPI spec; errors are problem+json
- [ ] UI: keyboard accessible, labelled, uses design tokens (no raw colours)
- [ ] Docs/ADR updated if a decision changed
