# 0006. Verify RS256 JWTs from an external IdP; use a mock IdP locally and for demos

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
In production, patients would authenticate through a national strong-identification service
(e.g. Suomi.fi) and staff through the organisation's IdP. The API must not hold passwords or
be able to mint tokens itself. Locally and in client demos we need realistic tokens without
any external dependency.

## Decision
- The API only **verifies** RS256 JWTs: the algorithm is pinned (no `alg=none` or algorithm
  confusion), and `iss`, `aud`, `exp` and `sub` are required. Tokens live 15 minutes.
- The API holds only the **public** key. Outside `local`/`test`, startup fails fast if no
  public key is configured.
- `careslot.mock_idp` issues tokens for four synthetic demo users. It is mounted only when
  `CARESLOT_ENVIRONMENT != production`, it is imported lazily, and import-linter forbids
  business modules from depending on it.
- The token subject **is** the patient or clinician id. Authorisation is plain Python in the
  use cases (`Principal`), which is unit-testable without HTTP.
- Other patients' resources return **404, not 403**, so the API never confirms they exist.
- Login is rate-limited on **failed** attempts per client and username (5 per minute).

## Alternatives considered
- **HS256 shared secret:** any service that can verify tokens could also forge them.
- **Sessions/cookies:** workable, but this API is designed to be called by several clients,
  and bearer tokens kept in memory avoid CSRF.

## Consequences
- Swapping the mock for a real IdP is configuration (issuer, audience, key or JWKS), not code.
- The in-process rate limiter counts per replica. Production should enforce it at the
  gateway/WAF or in a shared store (stated in the code).
- An erased patient's IdP account is not deactivated by this service. In production the IdP
  integration would react to `PatientErased` (listed under Planned in the README).
