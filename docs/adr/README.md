# Architecture Decision Records

Short documents that capture one significant decision each: the context, what we decided,
what we rejected and what it costs us. They are written so a new developer (or an
interviewer) can understand *why* the code looks the way it does.

| # | Decision | Status |
|---|---|---|
| [0001](0001-modular-monolith.md) | Modular monolith with enforced module boundaries | Accepted |
| [0002](0002-in-process-event-bus.md) | In-process, transactional domain event bus | Accepted |
| [0003](0003-column-level-envelope-encryption.md) | Column-level envelope encryption with a blind index | Accepted |
| [0004](0004-append-only-hash-chained-audit-log.md) | Append-only, hash-chained audit log | Accepted |
| [0005](0005-postgresql.md) | PostgreSQL as the single datastore | Accepted |
| [0006](0006-authentication-mock-idp-rs256.md) | RS256 JWTs from an external IdP; mock IdP for local and demo | Accepted |
| [0007](0007-consent-as-decision-history.md) | Consent as an append-only decision history | Accepted |
| 0008 | AI assistant: mock provider, pseudonymised input, validated output | Planned (written with the implementation) |
| [0009](0009-api-first-contract.md) | API-first: committed OpenAPI contract, problem+json, contract tests | Accepted |
| [0010](0010-uv-for-python-dependencies.md) | uv for Python dependency management | Accepted |
| [0011](0011-tailwind-semantic-design-tokens.md) | Tailwind CSS with semantic design tokens | Accepted |

**Writing a new ADR:** copy [template.md](template.md), take the next number, open a PR. An ADR
is never edited to change its decision; it is *superseded* by a new one that links back.
