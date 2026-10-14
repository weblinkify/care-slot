# Non-functional requirements

Targets for a production deployment serving one hospital district (roughly 500k residents,
~200 clinicians). Numbers are starting points to be validated with real load data.

## 1. Service level objectives (booking API)

| SLI | SLO | Measured how |
|---|---|---|
| **Availability**: share of valid requests (non-4xx) answered without a 5xx | **99.9 %** per 30 days (~43 min error budget) | Load balancer / API gateway metrics |
| **Latency**: `POST /appointments`, `GET /clinicians/{id}/slots` | **p95 < 300 ms**, p99 < 800 ms | OTel request spans (`http.route` template) |
| **Latency**: all other `/api/v1` reads | p95 < 200 ms | OTel |
| **Correctness**: double bookings | **0**, enforced by a DB constraint, not an SLO | Integration race test; periodic data check |
| **Audit completeness**: patient-data access without an audit entry | **0**, enforced by the same transaction | Design (ADR-0004); chain verification job |

**Error-budget policy:** if more than 50 % of the monthly budget is burned, feature work pauses
in favour of reliability work until the burn rate recovers.

**Why 99.9 % and not 99.99 %?** Booking is important but not life-critical: patients can phone
the clinic. 99.99 % would require multi-region active-active with distributed consensus. That
cost and complexity is better spent elsewhere, and it can be revisited if the service becomes
critical-path for emergency care.

## 2. Capacity and scaling

- **Expected load:** ~50 req/s average, ~300 req/s at peak (Monday 08:00, when slot releases
  open). Writes (bookings) are ~5 % of traffic.
- **Stateless API:** scale horizontally behind a load balancer. All state lives in
  PostgreSQL; tokens are self-contained JWTs. Before scaling beyond one replica, move rate
  limiting to the gateway or Redis (see THREAT_MODEL).
- **Database:** a single primary handles this comfortably. Scale vertically first, then add a read
  replica for slot searches and clinician schedules. Bookings and audit writes stay on the
  primary.
- **Known contention point:** audit appends are serialised by an advisory lock (ADR-0004).
  At ~5 ms per append this allows roughly 200 audited writes/s. Sharding the chain is the
  next step if we approach it.
- **Connection pooling:** SQLAlchemy pool per replica plus PgBouncer (transaction mode) in front
  of PostgreSQL once replicas × pool size approaches `max_connections`.

## 3. Caching strategy

| What | Cache? | Why |
|---|---|---|
| Clinics and clinicians list | Yes, ~5 min (HTTP `Cache-Control` on that endpoint, or in-memory) | Rarely changes, not personal data |
| Free slots | Very short (≤ 10 s) or not at all | Staleness causes booking conflicts; the 409 path handles it gracefully |
| Anything with patient data | **Never** in shared caches | `Cache-Control: no-store` on every API response; React Query cache is cleared on sign-out |
| Static frontend assets | 1 year, immutable (hashed filenames) | `index.html` is `no-cache` so deploys take effect immediately |

## 4. Backup and disaster recovery

| | Target |
|---|---|
| **RPO** (max data loss) | ≤ 5 minutes |
| **RTO** (max downtime after disaster) | ≤ 1 hour |

- Managed PostgreSQL with **point-in-time recovery** (continuous WAL archiving, 35-day
  retention) and zone-redundant high availability (synchronous standby in another zone).
- **Geo-redundant backups** to a paired region within the EU/EEA for data residency.
- **Encryption keys are part of the backup.** KEKs live in the KMS / key vault with soft-delete
  and purge protection. Restoring a database without its KEKs restores ciphertext only.
- **Restore drills quarterly:** restore into an isolated environment, run migrations,
  `GET /audit-log/verify`, and the E2E suite. A backup that has never been restored is a hope,
  not a backup.
- **Infrastructure is code** (`infra/terraform`), so the environment can be rebuilt in another
  region from source.

## 5. Security and compliance (non-functional)

- Data residency: all data and backups in EU/EEA regions.
- Encryption in transit (TLS 1.2+) and at rest (platform encryption + column encryption for
  identity codes, ADR-0003).
- Retention: booking data is deleted 730 days after the appointment (configurable;
  `careslot.jobs.retention`, run daily). The audit log is retained per legal requirements and
  archived, never edited.
- Observability without personal data: route templates, IDs and trace IDs only.

## 6. Observability

- **Traces:** OpenTelemetry for every request and SQL statement, exported over OTLP.
- **Logs:** structured JSON with `trace_id`; no personal data.
- **Health:** `/health` (liveness, no dependencies) and `/ready` (database reachable).
- **Alerts** (multi-window burn rate): page on a 2 % error-budget burn within 1 h; ticket on
  10 % within 3 days. Plus: audit-chain verification failure (page), retention job failure (ticket).

## 7. Cost considerations

- The modular monolith (ADR-0001) means one service, one database and one pipeline. That is the
  biggest cost lever, in both cloud spend and engineering time.
- Right-size first, scale out second: two small API replicas across zones plus one HA
  PostgreSQL covers the expected load.
- Scale to fewer replicas outside clinic hours; the database stays up.
- Prefer managed services (PostgreSQL, key vault, container platform) over self-run
  equivalents. Engineering hours cost more than the managed premium at this scale.
- AI assistant: provider cost is per token; inputs are minimised by design (ADR-0008), which
  is both a privacy and a cost control. A per-day request cap and caching of one summary per
  clinician per day bound the spend.
