# Worked example: "Add a cancellation reason"

This is the reference solution to the [onboarding](onboarding.md) first task. It walks through
one small feature across **every layer** and explains *why* each layer exists. Try the task
yourself first, then compare:

```bash
git fetch origin
git diff main...origin/example/cancellation-reason      # the complete, tested change
```

The branch passes the full gate: unit, integration, contract and E2E tests, lint and types.
It is deliberately not merged, so the task stays available for the next new developer.

---

## 0. Clarify the requirement before coding

> *"When patients cancel, let them tell us why, so clinics can see why slots go unused."*

Questions a good engineer asks first, and the answers we chose:

| Question | Decision | Why |
|---|---|---|
| Free text or a list? | **Fixed list** | A text box invites "my back pain got worse": that is health data (GDPR special category) we do not need. Data minimisation is a design decision, not a cleanup task. |
| Required? | **Optional** | Asking is fine; forcing patients to justify themselves is not. |
| Who sees it? | Aggregated statistics only (later) | It is still about a person's care. Nothing in this change displays it to staff. |
| Breaking change? | **No** | Old clients that POST `/cancel` with no body must keep working inside `/api/v1`. |

Writing these down in the PR description saves a review round.

---

## 1. Domain: the business rule lives here

`backend/src/careslot/modules/scheduling/domain/model.py`

```python
class CancellationReason(StrEnum):
    """Why a patient cancelled. A closed list on purpose - never free text ..."""
    SCHEDULING_CONFLICT = "scheduling-conflict"
    FEELING_BETTER = "feeling-better"
    BOOKED_ELSEWHERE = "booked-elsewhere"
    OTHER = "other"

def cancel(self, *, now: datetime, reason: CancellationReason | None = None) -> None:
    self._ensure_changeable(now)          # existing rules still apply (2-hour cut-off)
    self.status = AppointmentStatus.CANCELLED
    self.cancelled_at = now
    self.cancellation_reason = reason
    self.pending_events.append(
        AppointmentCancelled(appointment_id=self.id, patient_id=self.patient_id, reason=reason)
    )
```

**Why here?** The domain is pure Python with no FastAPI or SQLAlchemy, so the rule can be read
and tested in milliseconds. Whoever cancels (HTTP today, a phone-booking integration tomorrow)
goes through the same method and gets the same behaviour.

**Why on the event?** Other modules may want it (e.g. a future statistics module). Events carry
IDs and enum values only, never free text, so adding it is safe.

## 2. Application: orchestration and authorisation

`application/services.py`: the use case just passes the reason through.

```python
def cancel(self, principal, appointment_id, reason: CancellationReason | None = None):
    appointment = self._get_own_appointment(principal, appointment_id)   # ownership (404 if not yours)
    appointment.cancel(now=self._clock(), reason=reason)
    self._repo.save(appointment)
    self._record_appointment(principal, "appointment.cancel", appointment)  # audit
    self._flush_events(appointment)
```

**Why a separate layer?** Authorisation, auditing and event publishing are the same for every
caller. They do not belong in the HTTP router (which would be skipped by a non-HTTP caller) or
in the domain (which knows nothing about who is calling).

## 3. API: the contract

`api/schemas.py` and `api/router.py`

```python
class CancelAppointmentIn(StrictModel):            # extra="forbid": unknown fields -> 422
    reason: CancellationReason | None = Field(default=None, description="... no free text by design.")

def cancel(appointment_id, principal, service, body: CancelAppointmentIn | None = None):
    # Body is optional so existing v1 clients that POST without one keep working.
    reason = body.reason if body else None
    return AppointmentOut.of(service.cancel(principal, appointment_id, reason))
```

**Why separate schemas from domain objects?** The public contract must stay stable while the
domain evolves. Pydantic validates at the edge: a free-text reason is rejected with a 422
problem response that does **not** echo the input back.

Then regenerate the contract and review the diff like code:

```bash
make openapi          # updates api/openapi.json and frontend/src/api/schema.d.ts
git diff api/openapi.json
```

## 4. Infrastructure: persistence and the migration

`infrastructure/models.py` adds the column and a CHECK constraint (defence in depth: the
database refuses values outside the list even if a future code path forgets to validate).
`infrastructure/repository.py` maps the column to and from the enum. That mapping is the
*only* place that knows both shapes.

The migration (`migrations/versions/…_appointment_cancellation_reason.py`):

```python
def upgrade() -> None:
    op.add_column("sched_appointments",
                  sa.Column("cancellation_reason", sa.String(length=32), nullable=True))
    op.create_check_constraint("valid_cancellation_reason", "sched_appointments",
        "cancellation_reason IN ('scheduling-conflict', 'feeling-better', 'booked-elsewhere', 'other')")
```

Three lessons in one file:

1. **Ask before touching migrations** (AGENTS.md). They change shared state and are hard to undo.
2. **Zero-downtime:** a *nullable* column with no default is a metadata-only change in
   PostgreSQL. There is no table rewrite or long lock, and the old app version keeps working
   during a rolling deploy.
3. **Read what autogenerate produced.** `alembic revision --autogenerate` did *not* include
   the CHECK constraint (autogenerate does not detect them). It was added by hand. Always
   test the round trip:
   ```bash
   uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head
   uv run alembic check      # model and migrations agree
   ```

## 5. Tests: one per level, each proving something different

| Level | Test | Proves |
|---|---|---|
| Unit | `test_cancel_records_an_optional_reason_on_the_event`, `test_reason_is_optional` | The rule and the event, in milliseconds |
| Integration | `test_cancel_with_a_reason_from_the_closed_list` | Round trip through HTTP, the ORM and real PostgreSQL |
| Integration | `test_free_text_reasons_are_rejected` | The privacy decision is enforced, and input is not echoed |
| Integration | `test_cancel_without_a_body_still_works_for_existing_clients` | Backwards compatibility within v1 |
| Contract | (automatic) | The new body and field match the published OpenAPI |
| E2E | `booking.spec.ts` picks a reason before confirming | The journey works in a browser and passes axe |

Note the negative test. The interesting behaviour is often what must **not** happen.

## 6. Frontend: the same rule, made usable

- `features/booking/api.ts`: the mutation sends `{ reason }`. Types come from the regenerated
  contract, so a typo in a reason value is a **compile error**.
- `MyAppointmentsPage.tsx`: "Cancel" now opens a small panel with an optional `<Select>` and a
  "Confirm cancellation" button. It's a deliberate two-step action, it is labelled, and it is
  keyboard-accessible.
- Styling uses existing primitives and semantic tokens (`bg-surface-muted`,
  `variant="danger"`). No new colours; `cn()` merges the width override.
- `mocks/handlers.ts`: the client-demo API learns the same rule, so the Vercel demo stays honest.

## 7. Before opening the PR

```bash
make check && make e2e
```

Then fill in the PR template, including **AI assistance used?** if you used a tool. Expect
review questions like "why not free text?" or "is the migration safe for a rolling deploy?".
This document is the answer key.
