# 0001. Use a modular monolith with enforced module boundaries

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
CareSlot has five clearly separable business capabilities: scheduling, patients, consent,
audit and an AI assistant. A small team will build and run it. Healthcare adds strict
consistency needs: an appointment and its audit entry must commit together, and erasing a
patient must reliably affect every capability.

Microservices would give independent deployment and scaling, but at the cost of distributed
transactions (or sagas), network failure modes between every capability, several databases
to secure, back up and audit, and an operations burden the team does not need yet.

## Decision
One deployable FastAPI application, internally split into bounded-context modules under
`backend/src/careslot/modules/`. Each module:

- has `domain/`, `application/`, `infrastructure/` and `api/` layers, with dependencies
  pointing inwards (api -> infrastructure -> application -> domain);
- owns its tables (prefix `sched_`, `pat_`, `con_`, `aud_`, ...) and never reads another
  module's tables, and has no foreign keys into them;
- exposes a small public interface in its `__init__.py` (events, a few query functions);
- talks to other modules only through that interface or through domain events (ADR-0002).

These rules are **enforced in CI** by import-linter (`backend/.importlinter`): layer
contracts per module, one boundary contract per module, the shared kernel may not depend on
modules, and modules may not depend on the mock IdP. A violation fails the build, whether a
human or an AI agent wrote it.

## Alternatives considered
- **Microservices from day one:** rejected. The costs above, for no current scaling need.
- **Traditional layered monolith (one big domain):** rejected. Nothing stops scheduling code
  from querying patient tables, so it erodes into a "big ball of mud", and a later split
  becomes a rewrite.

## Consequences
- One transaction can span modules (e.g. a booking and its audit entry), with no sagas.
- A module can later be extracted into a service: its tables are already separate, and its
  public interface and events become the service API. The event bus is designed for that path.
- Shared deployment: a bad release affects all capabilities. This is mitigated by the CI gates and
  by keeping releases small.
- Module boundaries need discipline. The import-linter contracts make that discipline
  automatic rather than relying on code review alone.
