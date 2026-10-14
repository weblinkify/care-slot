# 0004. Keep an append-only, hash-chained audit log in the same database

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
Healthcare regulation (in Finland, e.g. the Client Data Act) and GDPR require that we can
show **who accessed which patient's data, when and why**. The log must be complete (no
access without an entry), trustworthy (not silently editable, even by insiders), and it must
survive a patient's erasure.

## Decision
- Every module reports access through a small port, `careslot.shared.audit.AuditSink`. The
  audit module implements it; use cases call it for every *successful* read or write of
  patient data, with a purpose (`AccessReason`).
- The audit entry is written **in the same transaction** as the access. A successful access
  cannot commit without its entry, and a failed request leaves neither.
- **Append-only, enforced by the database:** a trigger rejects `UPDATE`, `DELETE` and
  `TRUNCATE` on `aud_entries` for every role. In production the application role
  additionally has only `INSERT`/`SELECT` on the table.
- **Tamper-evident:** each entry stores `hash = SHA-256(prev_hash || canonical entry)`. Any
  edit, deletion or reordering breaks every later hash; `GET /audit-log/verify` reports the
  first broken entry. This catches even someone privileged enough to disable the trigger
  (tested).
- Appends are serialised with a transaction-scoped advisory lock, so concurrent writers keep
  one linear chain (tested with 4 parallel writers).
- Reading the audit log is itself audited. The log contains IDs only (pseudonymous), so it is
  retained after erasure without identifying the person.

## Alternatives considered
- **Application logs as the audit trail:** not reliably complete, easy to lose, easy to
  edit, and they mix operational and legal data.
- **Separate audit database or service:** an audit write could fail independently of the
  access, which reintroduces a completeness gap or requires an outbox.
- **External immutable store (WORM storage, ledger database):** the stronger option for
  production *in addition*. See Consequences.

## Consequences
- Completeness by construction, and tampering is detectable rather than merely discouraged.
- **The advisory lock serialises audit writes** across the system. That's fine at clinic
  scale; it becomes a ceiling at high write rates. Mitigations, in order: shard the chain
  (e.g. one chain per day or per patient-hash bucket), then periodically anchor each chain's
  head hash to external WORM storage so even a full-database rewrite is detectable.
- Verification is O(n). In production, run it as a scheduled job and checkpoint verified
  heads.
