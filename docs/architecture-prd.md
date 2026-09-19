# PRD: Certificate Automation Module

**Document status:** Draft v1.0 — supersedes ADR-001 design notes, incorporates senior review corrections
**Owner:** Bhargava
**Consumers:** Parent dashboard team (integration contract only — they don't own internals)
**Last updated:** 2026-06-25

---

## 1. Problem Statement

Event-organizing teams currently generate certificates manually in Canva and send them one-by-one via email. This doesn't scale past ~50 participants, has no retry safety, no delivery tracking, and no approval gate before emails go out. We're building a self-contained, plug-in module the dashboard calls through a small set of ports — the dashboard is never modified to support it.

## 2. Goals

- Accept participant data from Excel, Google Sheets, manual entry, or DB — normalized into one shape, **frozen as an immutable snapshot at import time**.
- Generate certificates against a dashboard-owned, **version-pinned** template.
- Survive a crash mid-batch without duplicate generation or duplicate emails.
- Never send an email without an explicit human approval step.
- Report live progress (`742/1000 generated`) without polling overhead.
- Scale from 1 to 50,000 participants by adding workers, not by redesigning.

## 3. Non-Goals

- Event registration, attendance, ticketing — owned by the dashboard.
- Template design/editing — owned by the dashboard (Canva-side).
- WhatsApp/SMS delivery — explicitly deferred to Phase 7, not MVP.

## 4. Updated Domain Model (post-review)

### 4.1 Batch FSM — corrected

```python
class BatchStatus(Enum):
    CREATED
    IMPORTING
    VALIDATING
    READY_FOR_GENERATION

    GENERATING
    GENERATED

    AWAITING_APPROVAL

    SENDING

    COMPLETED
    PARTIAL_SUCCESS     # e.g. 998/1000 succeeded — NOT the same as FAILED
    FAILED
    CANCELLED
```

**Correction applied:** a batch with 2 failures out of 1000 is `PARTIAL_SUCCESS`, not `FAILED`. This distinction is load-bearing for the dashboard's reporting UI and for deciding whether a retry is even necessary.

### 4.2 Import becomes a snapshot, not a live connection

`stream()` still avoids loading everything into memory, but its output is **persisted to the `participants` table immediately**, and the batch transitions to `READY_FOR_GENERATION` only once that snapshot is durable. Google Sheets / Excel can change after that — it no longer matters, because generation reads from `participants`, never from the live source again.

### 4.3 Template is version-pinned

```python
Batch(template_id=123, template_version=4)
```

If someone edits the template mid-batch, in-flight and historical certificates remain traceable to the exact version that produced them.

### 4.4 Task-level granularity (the biggest structural addition)

```
Batch
  └─ Participants
       └─ GenerationTasks  ──► Certificates
                                    └─ DeliveryTasks ──► Deliveries
```

`GenerationTasks` and `DeliveryTasks` are the unit of retry — at 50,000 rows, "regenerate the whole batch" is not an acceptable retry story. Pause/resume/retry must operate at **task granularity**, not batch granularity.

### 4.5 Idempotency key — corrected

- ~~`sha256(batch_id + email + template_id)`~~ — rejected, breaks if participant data is edited mid-batch.
- **Now:** `certificate_id` is generated once, durably, at certificate-creation time. `delivery_idempotency_key = sha256(certificate_id)`. Stable regardless of what changes upstream.

### 4.6 Generation concurrency — no longer frozen in the design

The earlier `ProcessPoolExecutor` assumption is **demoted from decision to hypothesis**. Whether rendering is CPU-bound (Pillow/ReportLab text overlay) or I/O-bound (template fetch + S3 upload + DB write dominate) depends on implementation details not yet benchmarked. The module exposes a `GenerationEngine` interface; the concrete strategy (`ThreadPoolExecutor` / `ProcessPoolExecutor` / Dramatiq actor concurrency) is selected **after benchmarking at 1k/5k/10k rows in Phase 3**, not assumed up front.

### 4.7 Delivery provider policy, not a hardcoded rate

```python
class ProviderPolicy(Protocol):
    rate_per_sec: float
    burst_capacity: int

class ResendPolicy: rate_per_sec = 10; burst_capacity = 10
class SMTPPolicy:   rate_per_sec = 2;  burst_capacity = 5
```

`TokenBucket` is constructed from whichever policy is active — never a magic number in the send path.

### 4.8 Storage — signed URLs, never in-memory attachments at scale

`Generate → Store → Get signed URL → attach-or-link at send time`. Holding 1000 × 2MB PDFs in worker memory during a send pass is the kind of mistake that only shows up under real load — designed out now.

### 4.9 `EmailProvider` → renamed `DeliveryProvider`

Future channels (`WhatsAppProvider`, `SMSProvider`) implement the same `Protocol` without touching the delivery engine — deferred to Phase 7, but the interface name shouldn't need a breaking rename later.

### 4.10 `PreviewProvider` — what exactly does a human approve?

Before `AWAITING_APPROVAL` is reachable, a `PreviewProvider` renders: first 5 certificates, 5 random certificates, and the validation failure report. The approval gate isn't just a button — it's a button with evidence behind it.

### 4.11 Progress tracking — atomic shared counters

```python
batch_progress: { generated_count, sent_count, failed_count }
```
Updated atomically (Redis `INCR` or a DB row with `SELECT ... FOR UPDATE`) by every worker. `GET /batch/{id}` reads this directly — no aggregation query over thousands of task rows on every poll.

## 5. Updated API Contract

```
POST   /certificate/batches                  # source descriptor + template_id + template_version
GET    /certificate/batches/{id}              # status, batch_progress, links
POST   /certificate/batches/{id}/generate     # 202, enqueues GenerationTasks
GET    /certificate/batches/{id}/preview      # NEW — sample certs + failure report
POST   /certificate/batches/{id}/approve      # NEW — explicit gate, separate from /send
POST   /certificate/batches/{id}/send         # 202, enqueues DeliveryTasks
GET    /certificate/batches/{id}/report       # final per-task breakdown
```

`/approve` is split from `/send` deliberately — approval is a permission decision, sending is an execution trigger. Different RBAC checks may apply to each.

## 6. Agile Delivery Plan — Phased, Each Phase Independently Demoable

Each phase produces a **working, demoable vertical slice** — not a horizontal layer (e.g., "all the database code") that can't be shown to anyone until everything else is also done. You should be able to stop after any phase and have something that runs end-to-end, just with a narrower scope.

### Phase 0 — Contracts & Walking Skeleton *(Sprint 0, ~3–5 days)*
**Goal:** Lock the interfaces before any implementation exists.
**Scope:** Define `ParticipantSource`, `TemplateProvider`, `StorageProvider`, `DeliveryProvider`, `GenerationEngine` as `Protocol`s. Stand up FastAPI skeleton with the 7 endpoints returning mocked responses. Postgres schema migrated (empty tables).
**Deliverable:** `POST /batches` → `GET /batches/{id}` round-trips against a real DB, with a stub `ManualEntrySource`.
**Definition of Done:** Dashboard team can integrate against the contract even though internals are fake.
**Out of scope:** Real generation, real sending, real queueing.

### Phase 1 — Single-Source Generation, No Queue, No Send *(Sprint 1, ~1 week)*
**Goal:** Prove the rendering pipeline works at all, synchronously, for small N.
**Scope:** `ManualEntrySource` + `ExcelSource` only. `TemplateProvider` against a real dashboard template. Synchronous generation (no worker pool yet) capped at N ≤ 50. Certificates land in real `StorageProvider` (S3/Supabase).
**Deliverable:** Upload an Excel sheet of 20 names → download 20 real certificate PDFs.
**Definition of Done:** A user can go from spreadsheet to PDFs with zero email involvement.
**Out of scope:** Google Sheets, DB source, async, approval gate, sending.

### Phase 2 — Import Snapshot, Validation, Multi-Source *(Sprint 2, ~1 week)*
**Goal:** Apply the review's correction — make import immutable and add the remaining sources.
**Scope:** `GoogleSheetSource`, `DatabaseSource`. Import persists to `participants` table immediately (snapshot). Validation pass produces a structured failure report (missing email, invalid format, duplicates). Batch FSM gains `IMPORTING` → `VALIDATING` → `READY_FOR_GENERATION`.
**Deliverable:** Connect a live Google Sheet, import 500 rows, see a validation report with 3 deliberately-broken rows flagged — and the sheet can change afterward without affecting the batch.
**Definition of Done:** Editing the source after import provably does not change the batch.

### Phase 3 — Scale Generation: Benchmark, Queue, Progress *(Sprint 3, ~1–1.5 weeks)*
**Goal:** Resolve the "ProcessPool vs ThreadPool vs Dramatiq" question with data, not assumption.
**Scope:** Wire Redis + Dramatiq (or Celery). Implement `GenerationTasks` at task granularity. Run a benchmark suite at 1k/5k/10k synthetic rows across `ThreadPoolExecutor`, `ProcessPoolExecutor`, and pure Dramatiq actor concurrency. Implement atomic `batch_progress` counters. Async `/generate` returns 202.
**Deliverable:** Generate 5,000 certificates; dashboard polls `GET /batches/{id}` and watches `generated_count` climb in real time; benchmark report committed to the repo documenting which concurrency strategy won and why.
**Definition of Done:** The concurrency strategy in `GenerationEngine` is chosen from measured data, written down, and can be revisited if rendering logic changes.

### Phase 4 — Preview & Human Approval Gate *(Sprint 4, ~3–5 days)*
**Goal:** Make "no auto-send" structural, with evidence behind the approval.
**Scope:** `PreviewProvider` (first-5, random-5, failure report). `GET /preview` endpoint. `/approve` as a distinct, guarded FSM transition — `SENDING` unreachable without it.
**Deliverable:** Generate a batch, view a preview with intentionally-wrong data, reject it, fix the source, re-import, regenerate, approve.
**Definition of Done:** Attempting `/send` on a non-approved batch returns a hard error, not a warning.

### Phase 5 — Rate-Limited Delivery Engine *(Sprint 5, ~1 week)*
**Goal:** Send safely at volume.
**Scope:** `DeliveryProvider` interface (renamed from `EmailProvider`) with `ResendPolicy`/`SMTPPolicy`. `TokenBucket` + bounded `asyncio.Semaphore`. `DeliveryTasks` at task granularity. Idempotency via `certificate_id`-derived key with a DB unique constraint. Signed-URL attachment (no in-memory PDFs at send time).
**Deliverable:** Approve a 1,000-row batch, send it, kill the worker process at row 400, restart it — verify no duplicate emails and the remaining ~600 get sent.
**Definition of Done:** The crash-and-resume test above is a repeatable, scripted test, not a manual claim.

### Phase 6 — Resilience & Observability *(Sprint 6, ~1 week)*
**Goal:** Operate this in production without guessing why something failed.
**Scope:** `PARTIAL_SUCCESS` / `CANCELLED` states wired through. Per-task error capture in `deliveries.error`. Provider throttle (`429`) detection feeding back into the active `ProviderPolicy`. Metrics: counters per `BatchStatus` transition, per-provider send latency.
**Deliverable:** A batch with 2% deliberately-injected failures completes as `PARTIAL_SUCCESS` with a downloadable per-row error report — not silently swallowed and not a hard `FAILED`.
**Definition of Done:** On-call can answer "why did certificate #482 fail" from the `deliveries` table alone, no log spelunking.

### Phase 7 — Extensibility & Monetization Hooks *(Sprint 7+, backlog)*
**Goal:** The features that make this a product, not a script.
**Scope:** `WhatsAppProvider`/`SMSProvider` behind the existing `DeliveryProvider` interface. Public verification pages (`/verify/{certificate_id}`). Per-batch usage metering for billing. Delivery analytics dashboard (open rate, bounce rate).
**Deliverable:** Demo a WhatsApp-delivered certificate without touching the delivery engine's core code — the proof that the Phase 0 interfaces actually held.
**Definition of Done:** Adding a new channel required zero changes to `Batch`, `GenerationEngine`, or the FSM.

## 7. Cross-Phase Risks & Open Questions

| Risk | Phase introduced | Mitigation |
|---|---|---|
| Concurrency strategy chosen too early, wrong for real rendering cost | 3 | Benchmark gate before freezing — explicitly not assumed in this PRD |
| Provider rate-limit policy hardcoded and silently wrong for a new provider | 5 | `ProviderPolicy` is a first-class interface, not a constant |
| Large batch (50k+) makes single-batch retry too coarse | 3, 5 | Task-level (`GenerationTasks`/`DeliveryTasks`) granularity from Phase 3 onward |
| Dashboard RBAC model doesn't map cleanly to `/approve` vs `/send` split | 4 | Flagged as open question for dashboard team — needs their sign-off, not assumed |
| Template edited mid-flight invalidates in-progress certs | 2 | `template_version` pinned at batch creation |

## 8. Success Metrics

- Phase 1–2: Manual QA only (functional correctness).
- Phase 3: p95 generation time for 5,000 rows ≤ target set after benchmarking (no pre-committed number — that's the point).
- Phase 5: Zero duplicate sends across 3 induced-crash test runs.
- Phase 6: 100% of failed deliveries traceable to a specific error reason without log access.
- Phase 7: New delivery channel added with 0 modified files outside its own adapter.
