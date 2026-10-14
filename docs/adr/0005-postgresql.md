# 0005. Use PostgreSQL as the single datastore

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
We need strong transactional guarantees (no double booking, an audit entry with every
access), constraints the database itself enforces, and a mature managed offering in Nordic
cloud regions with point-in-time recovery.

## Decision
PostgreSQL 16 for everything, accessed with SQLAlchemy 2 and versioned with Alembic.
We deliberately use PostgreSQL features where they carry a business rule:

- a **partial unique index** (`one booked appointment per slot`) is the real double-booking
  guard. The application check only gives a friendlier error. A two-thread race test proves
  the index is what stops the second booking;
- **triggers** make the audit log append-only;
- **advisory locks** serialise the audit hash chain;
- `timestamptz` everywhere; naive datetimes are rejected in the app.

## Alternatives considered
- **Document store:** our data is relational and benefits from constraints and transactions.
- **Separate store per module now:** see ADR-0001. Table prefixes and no cross-module foreign
  keys keep that option open.

## Consequences
- Business invariants hold even if a future code path forgets the application-level check.
- Some logic lives in migrations (index, trigger). This is reviewed like code; migrations need
  human approval (AGENTS.md) and CODEOWNERS review.
- Tests run against **real PostgreSQL** via Testcontainers, never SQLite, because the
  partial index, trigger and advisory lock would not behave the same.
