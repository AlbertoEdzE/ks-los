# Officer AI (Agentic) — Functional Audit & Implementation Plan

This document answers:
1) What the officer side *should* do (as implied by the LNAI officer “shell” UX and backend behavior),  
2) What LOS already implements today,  
3) What is missing (especially AI/agentic integration), and  
4) A concrete plan to close the gaps without breaking borrower flows.

> Note: “Pixel-perfect LNAI UI” is treated as *a shell for required functionality*, not the primary goal. The goal is a professional officer experience integrated into a single LOS universe.

---

## 1) Officer-side functional requirements (implied by LNAI)

### A) Portfolio / Lead operations (officer “dashboard”)
- List leads/applications with meaningful status and assignment
- Select a lead and view:
  - current pipeline/phase
  - approval probability + blocker/action reasoning
  - recommended products
- Update lead metadata:
  - borrower name, status, assigned officer
- Provide cross-navigation into:
  - loan pipeline (loans created from that lead)
  - officer chat thread
  - AI quality / evaluation signals

### B) Loan pipeline operations (document + STP hold resolution)
- List loans and their phase/status
- Per loan:
  - document checklist statuses (missing/submitted/verified/rejected)
  - document upload/replacement
  - underwriting memo generation
  - phase movement (workflow progression)
- Detect “holds” and guide resolution steps

### C) Officer chat (human-in-the-loop + actions)
- View conversation transcript
- Send a message into the thread
- Surface “action results” that the assistant executed (e.g., loan created, phase moved)
- Allow officer to route/triage the conversation (manual review, escalation)

### D) Ops / Admin tools (supporting the AI system)
- Catalog management (loan products + required documents)
- Synthetic data generation (for testing/training)
- ML training and evaluation pipeline UI
- Observability dashboards and drift reporting
- Configuration switches (feature flags / safety)

### E) AI oversight & governance (Agentic + evaluation)
- Officer must be able to:
  - inspect agentic session state (intent, confidence, flags, checkpoints)
  - observe evaluation metrics (RAGAS, hallucination rate, latency/cost)
  - understand why the system is “stuck” and what’s needed next
  - resolve discrepancies and apply overrides (with audit trail)

---

## 2) What LOS already implements (current state)

### Implemented (core)
- Officer navigation and modern “glass” officer shell across all officer pages
- **Dashboard** (`/dashboard`): modern lead view (all leads) with:
  - approval probability + blockers/actions
  - recommended products
  - editable lead fields + save
  - cross-links (loan, chat, agentic console)
- **Pipeline** (`/pipeline`): modern loan view (all loans) with:
  - document checklist update + upload
  - phase selector (PATCH loan)
  - underwriting memo generation (POST loan memo)
- **Officer chat** (`/officer-chat`): lead thread review + messaging + action result surfacing
- **Loan products** (`/loan-products`): catalog CRUD UI
- **Synthetic data** (`/synthetic-data`): generate + stream progress
- **Training** (`/training`): ML training workflow UI
- **Metrics** (`/metrics`): MetricsDashboard (portfolio + admin AI quality)
- **Simulator** (`/simulator`): model simulator
- **Configuration** (`/configuration`): feature toggle UI

### Implemented (AI oversight)
- **Officer Agentic Console** (`/agentic-console`)
  - officer-only endpoints to list/get v3 agentic session state
  - transcript view of v3 session messages
  - embedded RAGAS/hallucination metrics (admin-auth gated)

### Implemented (cross-entity cohesion)
- Deep-link preselection by query param:
  - dashboard: `?leadId=...`
  - pipeline: `?loanId=...`
  - officer chat: `?conversationId=...`
  - officer hold: `?leadId=...` / `?loanId=...`
  - agentic console: `?sessionId=...`
- Lead ↔ loan linkage via `Loan.conversationId` (when present)

---

## 3) What is missing (critical gaps)

### Gap 1 — Canonical ID mapping between v2 and v3
Today, LOS has:
- v2: `Conversation.id` (officer dashboard + officer chat)
- v2: `Loan.conversationId` (links to conversation)
- v3: `V3ConversationState.session_id` (agentic runtime)

**Missing:** a reliable mapping guaranteeing which agentic session corresponds to which v2 conversation/loan.
This blocks:
- “Open agentic session for this lead”
- per-lead AI quality metrics consistency
- auditability and replay

### Gap 2 — Officer-controlled agentic actions (HITL controls)
We can *inspect* agentic state, but officers cannot yet:
- create/attach a v3 agentic session to a selected lead
- trigger/retry specific agentic steps (e.g., document validation, STP processing)
- approve/deny agentic suggestions with explicit audit trail

### Gap 3 — Governance & audit trail in UI
Missing:
- “who changed what” timeline for:
  - lead edits, document decisions, phase movement, overrides
- escalation workflow:
  - mark manual review required
  - assign to officer/queue
  - attach reasoning/notes

### Gap 4 — Unified “task” model for holds
The system identifies blockers (approval probability) and doc holds, but lacks:
- a first-class “task/hold” entity with:
  - severity, owner, SLA, reason codes
  - status transitions (open → in-progress → resolved)
  - reporting and dashboards

---

## 4) Implementation plan (scientific / rigorous, minimal risk to borrower)

### Phase 1 — Data model + mapping layer (high priority)
**Backend**
1. Introduce a mapping table:
   - `ConversationAgenticLink(conversation_id, session_id, created_at, created_by, status)`
2. Add officer-only endpoints:
   - `POST /api/officer/agentic/attach` (attach/create session for conversation)
   - `GET /api/officer/agentic/by-conversation/{conversation_id}` (resolve mapping)
3. Ensure strict RBAC + audit logging for these operations.

**Frontend**
1. Add a “Agentic session” section in dashboard + officer chat:
   - show if mapped session exists
   - button: “Open agentic session”
   - button: “Create/attach agentic session”

**Tests**
- unit: mapping creation and idempotency
- integration: attach session then fetch by conversation

### Phase 2 — HITL officer actions (agentic controls)
**Backend**
1. Add “command” endpoints (officer-only):
   - `POST /api/officer/agentic/{sessionId}/command`
     - allowed commands: `rerun_step`, `validate_documents`, `run_stp`, `recompute_recommendations`, `escalate`, `clear_escalation`
2. Persist command log + execution results.

**Frontend**
1. Agentic Console: “Commands” panel
2. Officer Chat: “AI actions” panel next to action results

**Tests**
- permissions
- command schema validation
- no borrower route changes

### Phase 3 — Audit trail + “task/hold” system
**Backend**
1. Create `OfficerTask` model:
   - `type` (approval_blocker, doc_hold, escalation, compliance_hold)
   - `entity` (conversation_id / loan_id)
   - `severity`, `status`, `owner`, `reason`, `details`
2. Auto-generate tasks from:
   - approval probability blockers
   - STP awaiting_documents + missing docs
   - escalation flags from agentic state

**Frontend**
1. Dashboard: “Tasks” list + filters
2. Pipeline: loan-level hold/task view
3. Officer metrics: task throughput and SLA

### Phase 4 — UX polish + visual regression gating
1. Extend the existing Playwright visual parity harness to cover:
   - officer nav header
   - dashboard, pipeline, metrics, loan products, officer chat
2. Introduce screenshot baselines and CI gate.

---

## 5) Answer to “does officer need AI developing parts?”
Yes. The officer surface is not just CRUD; it is the **human-in-the-loop control plane** for the agent:
- observe (state + quality)
- decide (approve/override/escalate)
- act (trigger steps, resolve holds)
- audit (traceability for every AI-driven operation)

