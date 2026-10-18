# Security policy

CareSlot handles (synthetic) health data, and it is built as if the data were real. This file
explains how to report a vulnerability and what happens next. It also points to where each
part of the security design is documented.

## Reporting a vulnerability

**Do not open a public issue, pull request or discussion for a security problem.**

Report it privately through GitHub: **Security → Report a vulnerability** on this repository
(GitHub private vulnerability reporting). Please include:

- what is affected (endpoint, module, file or commit);
- steps to reproduce, using the **synthetic seed data** (`make seed`) only;
- the impact you expect (e.g. one patient reading another's appointments);
- whether you think it is being exploited.

Do not include real personal data, and do not test against anyone else's deployment. Do not
paste unpatched vulnerability details into AI tools. The [AI policy §2](docs/ai-development-policy.md)
applies to reporters and maintainers alike.

### What happens next

| Step | Target |
|---|---|
| Acknowledge the report | 3 working days |
| First assessment and severity (CVSS v4) | 7 working days |
| Fix for Critical / High | 30 days |
| Fix for Medium / Low | 90 days |
| Public advisory and credit (if you want it) | when the fix is released |

We keep you updated while we work on it. If a report involves personal data in a real
deployment, the data protection officer is involved from day one, so the 72-hour GDPR breach
notification clock can be met.

## Supported versions

Only the latest commit on `main` (and the live demo built from it) receives security fixes.
There are no released versions to backport to.

## Scope

**In scope:** the backend (`backend/`), the frontend (`frontend/`), the security headers
(nginx and Vercel config), the CI workflow and the Terraform in `infra/`.

**Out of scope:**

- The **mock identity provider** used for local development and the demo. It is not mounted in
  production (`test_mock_idp_is_not_mounted_in_production`). Real flaws in how the API
  *validates* its tokens are in scope.
- The **demo password** `demo-password`. It is published on purpose.
- The **live demo** at careslot-demo.vercel.app. Its API is simulated in your browser, so
  there is no server-side data to reach. Report header or CSP issues, but do not load-test it.
- Missing rate limiting across replicas, WAF, DDoS or bot protection. These are known and
  listed in [THREAT_MODEL.md](THREAT_MODEL.md) under *Residual risks*.
- Findings that need a compromised developer machine or CI runner.

## Where the security design is documented

| Topic | Document |
|---|---|
| What the system does about security and GDPR, with the test that proves each control | [README → Security and GDPR](README.md#security-and-gdpr) |
| Threats to the booking flow (STRIDE), mitigations and residual risks | [THREAT_MODEL.md](THREAT_MODEL.md) |
| Risks from AI coding agents and the planned AI assistant | [docs/ai-risks.md](docs/ai-risks.md) |
| Rules for AI tools: approved tools, data never to put in prompts, review | [docs/ai-development-policy.md](docs/ai-development-policy.md) |
| Rules every contributor and agent follows | [AGENTS.md](AGENTS.md) §5–6, [docs/engineering-standards.md](docs/engineering-standards.md) §6 |
| Encryption at rest, audit log, auth, session cookie | ADRs [0003](docs/adr/0003-column-level-envelope-encryption.md), [0004](docs/adr/0004-append-only-hash-chained-audit-log.md), [0006](docs/adr/0006-authentication-mock-idp-rs256.md), [0012](docs/adr/0012-session-refresh-cookie.md) |

## Automated checks

Every change, from a person or an AI agent, passes the same gates:

- **Before commit:** `gitleaks`, `detect-private-key`, ruff, import boundaries, frontend lint.
- **In CI:** gitleaks over the full history, `pip-audit`, `npm audit --audit-level=high`,
  container build with an SPDX SBOM, a Trivy scan that fails on fixable HIGH/CRITICAL, and E2E
  checks of the security headers on nginx and Vercel.
- **Dependencies:** Dependabot. Lockfiles are committed.
- **Review:** [CODEOWNERS](.github/CODEOWNERS) requires owner review for migrations,
  `shared/crypto.py`, `shared/security.py`, the audit module, `AGENTS.md` and the AI policy.
  Protected branches cannot be pushed to directly.
