# Contributing to CareSlot

Thanks for helping. New here? Start with **[docs/onboarding.md](docs/onboarding.md)**: you
will have the stack running and your first change in review on day one.

## The short version

1. `make install && make up && make seed`. That gives you the whole stack with synthetic data
   and pre-commit hooks enabled.
2. Branch from `main`: `feat/<short-name>`.
3. Make a small change **with tests**. Read [AGENTS.md](AGENTS.md) for the rules that apply to
   everyone, human or AI.
4. `make check` (and `make e2e` for UI changes).
5. Open a PR using the template, including the **AI assistance** section, honestly.
6. Address review comments; squash-merge when green and approved.

## Where to read more

| Topic | Document |
|---|---|
| Standards: branching, commits, definition of done, test pyramid, review culture | [docs/engineering-standards.md](docs/engineering-standards.md) |
| Using AI tools: what is allowed, what is never pasted into prompts, how AI code is reviewed | [docs/ai-development-policy.md](docs/ai-development-policy.md) |
| Why the architecture looks like this | [docs/adr/](docs/adr/README.md) |
| A fully worked feature, layer by layer | [docs/example-feature-walkthrough.md](docs/example-feature-walkthrough.md) |
| Security model | [THREAT_MODEL.md](THREAT_MODEL.md) |
| SLOs, scaling, backup/DR | [docs/non-functional-requirements.md](docs/non-functional-requirements.md) |

## Things that will block a PR

- Missing tests, or tests that would pass without the change.
- Personal data anywhere: logs, fixtures, prompts, screenshots, commit messages. Synthetic
  data only.
- Crossing module boundaries (CI will tell you).
- A migration without prior agreement, or one that is not reversible.
- A new dependency without justification.
- Disabled, skipped or weakened tests or checks.

## Reporting a security issue

Do not open a public issue. Contact the maintainers privately; see the repository's security
policy.
