# Onboarding: productive on day one

Welcome! By the end of today you will have the whole system running, understand its shape,
have run every kind of test, and have a first small feature in review. Ask questions early.
Pairing with your onboarding buddy is expected, not a favour.

## Morning: run everything (≈ 30 min)

**Prerequisites:** Docker, Python 3.12, Node 22, [uv](https://docs.astral.sh/uv/), make.
Open the repo in VS Code and accept the recommended extensions (Ruff, ESLint, Prettier,
Tailwind CSS IntelliSense, Playwright). The workspace already points at the right Python
interpreter.

```bash
git clone git@github.com:weblinkify/care-slot.git && cd care-slot
make install      # backend + frontend deps, and the pre-commit hooks
make up           # db + api + web in Docker; generates local-only encryption keys into .env
make seed         # synthetic clinic, clinicians, 2 weeks of slots, demo patients
```

| Open | What you see |
|---|---|
| http://localhost:5173 | The app. Sign in with a demo button: `aino` / `eero` (patients), `dr.aava` (clinician), `admin`. Password: `demo-password`. |
| http://localhost:8000/api/v1/docs | Interactive API docs (from the committed OpenAPI contract) |
| `make up-observability` → http://localhost:16686 | Jaeger: every request and SQL statement as a trace |

Try it as each role: book as Aino, open her record as Dr. Aava (you will be asked *why*), then
look at the audit log as admin and press **Verify integrity**.

Something broken? `make reset` wipes local data and starts fresh.

## Late morning: understand the shape (≈ 1 h)

Read in this order. Each is short.

1. [README](../README.md): the problem, the architecture diagram and the module map.
2. [AGENTS.md](../AGENTS.md): the rules everyone follows (yes, they are written for AI agents;
   they work for humans too).
3. ADRs [0001](adr/0001-modular-monolith.md) (modules), [0004](adr/0004-append-only-hash-chained-audit-log.md)
   (audit) and [0003](adr/0003-column-level-envelope-encryption.md) (encryption).
4. Follow one request through the code: `POST /api/v1/appointments` →
   `modules/scheduling/api/router.py` → `application/services.py` (`book`) →
   `domain/model.py` (`Appointment.book`) → `infrastructure/repository.py`.
   Notice what each layer does *not* do.

## After lunch: run the tests (≈ 30 min)

```bash
make test-unit          # seconds - domain rules and authorisation
make test-integration   # real PostgreSQL in a throwaway container
make test-contract      # the API vs its OpenAPI contract (generated inputs)
make e2e                # browser journeys against `make up`, incl. accessibility scans
make check              # everything CI runs, locally
```

Then break something on purpose: remove the ownership check in
`SchedulingService._get_own_appointment` and run `make test-unit`. Watch which tests catch
it, then put it back. This is the fastest way to trust the safety net.

## Afternoon: your first task, "add a cancellation reason"

> Patients should be able to say *why* they cancel, so clinics can see why slots go unused.

It is small, but it touches every layer: **domain → API → migration → tests → UI**.

1. Branch: `git switch -c feat/cancellation-reason`.
2. Before coding, write down your answers to: free text or a list? Required or optional? Is it
   a breaking API change? (Hint: this is health care. Think about what patients would type.)
3. **Domain:** add the reason to `Appointment.cancel` and the `AppointmentCancelled` event.
   Write the unit test first.
4. **API:** accept it in `POST /appointments/{id}/cancel` without breaking existing clients;
   return it in `AppointmentOut`; run `make openapi` and read the contract diff.
5. **Migration:** *ask your buddy first* (team rule). Add a nullable column; check that it is
   safe for a rolling deploy; test upgrade, downgrade and upgrade.
6. **Tests:** an integration test for the happy path and one proving what must be rejected.
7. **UI:** let the patient pick a reason when cancelling. Use the existing `Field`, `Select`,
   `Button` primitives and design tokens; keep it keyboard-accessible.
8. `make check && make e2e`, then open a PR with the template.

Stuck, or finished? Compare with the reference solution and its explanation:
**[example-feature-walkthrough.md](example-feature-walkthrough.md)**.

## By the end of week one

- Pair on a review: read someone else's PR with the
  [review guidelines](engineering-standards.md#4-code-review-culture).
- Read the [threat model](../THREAT_MODEL.md) and the
  [AI development policy](ai-development-policy.md). Ask about anything that surprises you.
- Suggest one improvement to this onboarding guide. You are now its best reviewer.
