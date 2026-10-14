# 0009. API-first: a committed OpenAPI contract, problem+json errors, contract tests

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
The API has several consumers (web app, a client-demo mock, future integrations). If the
contract lives only in code, changes slip through review, and clients and mocks drift.

## Decision
- **The contract is a reviewed artefact:** `api/openapi.json` is generated from the code
  (`make openapi`) and committed. API changes show up as a readable diff in the PR. CI
  regenerates it and fails on drift.
- **Versioned paths:** `/api/v1`. Breaking changes require `/api/v2` alongside v1.
- **One error format:** every error is RFC 7807 `application/problem+json` with a stable
  `type` URI per error kind. The spec documents exactly that (`problem_openapi()`
  post-processes FastAPI's defaults). Validation errors never echo submitted input.
- **Clients are generated:** the frontend's TypeScript types come from the contract
  (`openapi-typescript`), and so does the demo mock's typing. CI fails if they drift.
- **The contract is a test oracle:** schemathesis generates requests for every operation and
  checks for 5xx responses, undocumented status codes and content types, and schema violations.

## Alternatives considered
- **Hand-written spec first, code generated from it:** stronger design-first discipline,
  but two sources of truth in a small team. We keep code-first generation and treat the
  committed spec as the design artefact under review.
- **GraphQL:** unnecessary for this resource-oriented domain.

## Consequences
- Contract tests found five real defects on their first run (missing `Allow` header,
  undocumented 400, mislabelled error content type, lax consent boolean, undocumented 429).
- Contract tests add roughly 40 s to CI. That's acceptable; tune `max_examples` if needed.
- Some rules cannot be expressed in OpenAPI (cross-field, state-dependent). The API answers
  them with documented 409/422 problems, and the "positive data acceptance" check is excluded
  with a written rationale.
