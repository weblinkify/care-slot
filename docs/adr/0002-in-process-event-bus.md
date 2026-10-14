# 0002. Use an in-process, transactional domain event bus

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
Modules must react to each other without importing each other's internals. Example: when a
patient exercises the right to erasure, scheduling must cancel future appointments and consent
must drop its history. Ordering and atomicity matter: a half-erased patient is a GDPR incident.

## Decision
`careslot.shared.events.EventBus` dispatches immutable `DomainEvent` dataclasses
**synchronously, inside the publisher's database transaction**. Handlers receive the event
and the session. Subscriptions are wired in one place, `careslot/wiring.py`, so the
cross-module dependency graph is visible at a glance.

Events are designed to be broker-ready from day one:
- they carry IDs only, never personal data;
- `to_message()` gives a flat, JSON-serialisable representation;
- publishers do not know who listens and handlers return nothing.

## Alternatives considered
- **Direct calls between modules:** creates compile-time coupling in both directions and
  hides the dependency graph.
- **Message broker now (Kafka / Service Bus / RabbitMQ):** gives eventual consistency, which
  then requires a transactional outbox, idempotent consumers, retries and dead-letter handling.
  That is real complexity for no current need.

## Consequences
- Erasure, booking and their side effects commit or roll back as one unit.
- A slow or failing handler slows or fails the publishing request. Handlers must stay small.
- **Migration path to a broker:** introduce a transactional outbox (`publish` writes
  `to_message()` to an outbox table in the same transaction; a relay forwards to the broker),
  then move individual handlers to consumers. Publishers do not change.
