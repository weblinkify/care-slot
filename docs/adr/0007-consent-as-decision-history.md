# 0007. Model consent as an append-only decision history

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
GDPR art. 7(1): the controller must be able to *demonstrate* consent. Art. 7(3): withdrawing
must be as easy as giving. Consent is per purpose, and the privacy notice text changes over
time.

## Decision
- Consent is a list of immutable `ConsentDecision` rows (patient, purpose, granted,
  decided_at, policy_version). The **current** state per purpose is the latest decision. No
  row is ever updated.
- Default is **not granted** (opt-in). Repeating the same decision is idempotent.
- Purposes are a closed enum (regional record sharing, research, AI summaries), and the API
  accepts only a strict JSON boolean (`0` or `"no"` is rejected; found by contract tests).
- Only the patient can decide. `ConsentGranted` and `ConsentWithdrawn` events let other
  modules react; `patient_has_consent()` is the public query.
- On erasure the history is deleted: no further processing happens, so proof is no longer
  needed.

## Alternatives considered
- **Boolean column per purpose:** loses the when and under which notice, so it cannot
  demonstrate anything.
- **Event sourcing the whole patient aggregate:** a heavier pattern than this one fact needs.

## Consequences
- Full audit of consent changes is available to the patient in the UI.
- Reads compute the latest decision per purpose, which is trivial at this size. Add a
  materialised view if needed.
