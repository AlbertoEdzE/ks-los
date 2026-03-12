# KS-LOS v2 — Gap Analysis & Migration Report (Overview 2)

**Date:** 2026-03-11  
**Scope:** Interpret the new target product definition + UI design, compare against current KS-LOS POC, and describe the concrete technical “jump” needed from the current state to the target.

## 0. Source Material Reviewed (as requested)

1. **Aditya transcript**: [/doc/00_planning/04_Aditya-LOS-1.txt](file:///Users/albertohernandez/Documents/projects/ks-los/doc/00_planning/04_Aditya-LOS-1.txt)  
2. **Feature formalization**: [/doc/00_planning/05_Agentic Loan Originating System.pdf](file:///Users/albertohernandez/Documents/projects/ks-los/doc/00_planning/05_Agentic%20Loan%20Originating%20System.pdf)  
3. **UI design that MUST be used** (full reference implementation / mock): [/doc/02_Loan-Navigator-AI](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI)

## 1. What the new documentation is actually asking for (my interpretation)

The new “north star” is no longer “a risk scoring demo with a chat UI”. The target is a **Loan Origination experience** with:

- A **Borrower-facing assistant** that feels like a senior loan advisor and actively guides the person through the lifecycle (not just “fill a form”).
- An **Officer-facing workspace** that turns conversations into operational work: qualification, pipeline movement, underwriting support, and next-best actions.
- A strong requirement that the system is **agentic in workflow terms**: it doesn’t just answer questions; it plans, extracts, checks, escalates, and advances pipeline states.

### 1.1 The 5 “wow” capabilities (convergent between transcript + PDF)

The PDF lists 5 features, and Aditya independently emphasizes the same set (often using similar wording). These are the core “v2 value props”:

1. **Borrowing Strategy Designer**
   - Input: borrower intent (“why money”), constraints, and context.
   - Output: a structured loan strategy (split secured/unsecured, different tenures, staged disbursement), plus explicit options like “lowest EMI / fastest approval / lowest total interest”.
   - Product implication: needs product catalog + eligibility rules + simulation (“what happens if…”).

2. **Approval Probability Navigator**
   - Output is *always-on*: approval likelihood + top blockers + top actions to improve odds + “fastest path to sanction vs best pricing path”.
   - This is not the same as a single risk score; it’s a continuous coaching panel that updates as inputs/documents arrive.

3. **Autonomous Application Completion Agent**
   - The system identifies missing items, requests the right document for the borrower type and loan type, detects mismatches, explains *why*, reminds automatically, and escalates exceptions.
   - This requires a document checklist engine + validation + workflow automation (reminders/escalations).

4. **Explainable Underwriting Copilot**
   - Output is a premium underwriting “memo”: borrower summary, strengths, risk flags, policy deviations, compensating factors, recommended conditions, alternatives.
   - This is a **loan officer artifact**, not borrower chat fluff.

5. **Pipeline Rescue + Next-Best-Action Console**
   - A system-level view that tells officers what to do today: which cases are close, which are likely to drop off, who is confused vs rate-sensitive vs ineligible, what can be saved by restructuring.
   - This is where “agentic” becomes operational: pipeline monitoring + prioritization + interventions.

### 1.2 The UI design in /doc/02_Loan-Navigator-AI expresses a concrete product shape

The Loan Navigator UI design isn’t a loose Figma—it's a working app skeleton with a full screen map:

- **Borrower Chat** (root): chat + phase tracker (top) + recommendation cards.  
  Reference: [chat.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/chat.tsx)
- **Officer Dashboard**: list of leads (conversations), seriousness score, fit score, detail panel.  
  Reference: [officer-dashboard.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/officer-dashboard.tsx)
- **Loan Pipeline board**: phases as columns, loans as cards, detail drawer.  
  Reference: [loan-pipeline.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/loan-pipeline.tsx)
- **Officer Lifecycle Chat**: officer role chat + pipeline/loans side panel.  
  Reference: [officer-chat.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/officer-chat.tsx)
- **Loan Product Catalog**: CRUD for products, required docs, eligibility criteria.  
  Reference: [loan-products.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/loan-products.tsx)

The design also formalizes the *data model* needed to support the UI:
Reference: [schema.ts](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/shared/schema.ts)

Core entities introduced there:

- Conversations, Messages
- Loan Phases
- Loans (a tracked object distinct from “conversation”)
- Loan Product Catalog (documents, criteria, ranges, etc.)

## 2. Current POC (what you have today)

Your current repository is a well-functioning POC, but it is centered around:

- A **Journey Coach chat** that can generate / retrieve a synthetic applicant profile and run a risk decision pipeline.
- A **credit profile view** panel and an **analysis progress indicator** (SSE-driven).
- A significant **MLOps/training workflow** implementation (config → training → evaluation → testing → deployment) and model management/rollback.

### 2.1 Frontend snapshot (current repo)

- Single-page login gate, then either:
  - User view: chat + progress bar + credit profile view  
  - Admin view: admin panels (training, simulator, metrics, etc.)
  Reference: [App.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/frontend/src/App.tsx)

### 2.2 Backend snapshot (current repo)

- Main chat endpoint: [/src/api/routers/agent_router.py](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/agent_router.py)
  - `POST /agent/chat` invokes LangGraph and returns:
    - chat response
    - credit profile
    - risk decision / reasoning
    - advice

- Progress stream endpoint (SSE): [/src/api/routers/chat_support_router.py](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/chat_support_router.py)
  - `GET /chat/progress/stream?full_name=...` emits steps such as lookup → inference → decision

- Training endpoints + orchestration: [/src/api/routers/training_router.py](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/training_router.py)
- Explain endpoint (feature importances fallback): [/src/api/routers/explain_router.py](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/explain_router.py)

### 2.3 Key constraints implied by the current POC

- Chat is **not** a first-class persisted entity (no “conversation list”, no “lead states”, no officer assignment).
- There is no “loan” object with lifecycle phases; there is a “credit profile / decision” output.
- The UI and backend are currently organized around “demo analysis”, not around “origination workflow”.

## 3. Does the new direction make sense? Yes — and it’s coherent

The transcript + PDF + UI design are aligned around a single idea:

> “A LOS is primarily an operational system. AI is valuable when it reduces work, prevents drop-offs, and increases approvals through structured guidance.”

Where the new direction is especially strong:

- It explicitly differentiates **borrower experience** vs **officer experience**.
- It makes “agentic” concrete by anchoring it in pipeline movement, document completion, underwriting memos, and next-best actions.
- It naturally justifies multi-agent orchestration (intent extraction, policy lookup, product selection, doc validation, risk model inference, summarization, compliance guardrails).

## 4. Challenges / Gaps (from current POC → target Loan Navigator)

This section is intentionally “fine-grained”, because the biggest risk here is underestimating how many small, connected shifts are needed.

### 4.1 UI/UX delta (big)

**Target UI** expects a multi-surface product:

- Borrower chat with phase tracker and recommendation cards
- Officer dashboard with lead scoring and drilldown
- Pipeline kanban
- Officer lifecycle chat (pipeline and loan management via chat)
- Product catalog management

**Current UI** is:

- One user screen (chat + generated credit profile)
- One admin screen (MLOps & tools)

**Implication:**

- The frontend must move from a “single demo flow” to a **multi-route app** with shared layout primitives and role-based navigation.
- The design in `/doc/02_Loan-Navigator-AI` is implemented with a UI stack (Radix + many components + wouter + react-query). Your current frontend dependencies are far lighter. If we “use the design”, we must either:
  - Port the UI components and adopt the same UI dependencies, or
  - Re-implement the design using your current frontend stack (but this risks visual drift and longer effort).

### 4.2 Domain model delta (the real gap)

The biggest missing piece is not “more prompts”; it’s **the operational object model**.

The Loan Navigator design implies these first-class objects:

- **Conversation**: a lead container (with status, seriousness score, fit score, next angle, assigned officer)
- **Message**: event log of dialogue (with metadata payloads)
- **LoanPhase**: ordered lifecycle stage definitions
- **Loan**: an application artifact that moves across phases and has structured fields
- **CatalogProduct**: product rules, required documents, constraints, features

Current POC is mainly built around:

- **ApplicantCreditProfile** (synthetic credit bureau shape)
- **RiskDecision** (approve/decline/manual-review + reasoning)
- **Training runs / model versions**

**Implication:**

- v2 must introduce persistence and domain objects that bridge chat → pipeline → underwriting → actions.
- Without this, features (3) and (5) cannot exist in a credible way, because they require “what is missing, what is next, what is stuck, what changed”.

### 4.3 Backend API delta (contract mismatch)

The Loan Navigator UI design expects APIs like:

- `POST /api/conversations` (create lead session, seed greeting)
- `POST /api/conversations/:id/messages` (send message, get structured intent analysis, phase updates, recommendations)
- `GET /api/conversations` (officer lead list)
- `GET /api/phases` and `/api/phases/active`
- `GET /api/loans` and phase movement
- `GET/POST/PATCH /api/catalog-products`

Your current backend exposes:

- `POST /agent/chat` (stateless-ish “chat returns profile + decision”)
- `GET /chat/progress/stream` (SSE)
- Training / explain / admin routes (which are v1 internal tooling, not v2 product surfaces)

**Implication:**

- To implement the UI design, the backend needs a new “product API layer” (even if internally it still calls your existing LangGraph graph and XGBoost model).
- The current endpoints can remain (especially training), but the v2 UI will primarily use the “conversation/loan/product” API contract.

### 4.4 Agent/AI delta (from “chat answers” → “workflow state changes”)

To deliver the 5 wow features, the agent layer must change in two ways:

1. **Structured outputs are mandatory**
   - The UI needs numbers, blockers, actions, recommended products, required docs, phase changes, and underwriting memo sections.
   - This means the LLM must output typed JSON (validated) and the backend must store + serve it reliably.

2. **Agents must be specialized by responsibility**
   - You already have a LangGraph-based approach, which is the correct foundation.
   - But v2 requires additional nodes/agents beyond “risk engine” and “advisory”:
     - Intent extraction and normalization (borrower + officer)
     - Product selection + scenario simulator (Borrowing Strategy Designer)
     - Probability & blockers analyst (Approval Navigator)
     - Document checklist generator + verifier + reminder scheduler (Autonomous Completion)
     - Underwriting memo composer (Explainable Underwriting)
     - Pipeline analyst (Next Best Actions)

**Implication:**

- v2 is not “add more prompts”. It’s “create a reliable state machine whose transitions are driven by validated structured outputs and deterministic business rules.”

### 4.5 ML/model delta (risk score is necessary, not sufficient)

Your current ML is oriented around a simplified credit risk score with a small feature set.

For the new features:

- Borrowing Strategy + Approval Navigator require *counterfactual reasoning*:
  - “If you reduce requested amount by 8%…”
  - “If you add co-applicant…”
  - “If you switch product…”
- Underwriting copilot requires:
  - Policy checks (territory + product + borrower type)
  - Clear explanation features and factors that map to those policies

**Implication:**

- The ML model can remain an XGBoost core, but the feature space must grow to include:
  - FOIR/DTI, income stability, debt structure, LTV, collateral flags, document completeness, etc.
- You will also need a “what-if engine”:
  - Either heuristics + rules on top of model outputs, or
  - A model that supports counterfactual explanations.

### 4.6 Workflow automation delta (documents, reminders, escalations)

Features (3) and (5) require automation primitives:

- Timers, reminders, SLAs
- Exception detection
- Assignment and escalation
- Audit trail of “what the agent did and why”

**Implication:**

- Even for a POC v2, you need a minimal job runner/scheduler concept (could be lightweight at first).

### 4.7 Security, compliance, and user roles delta

The Loan Navigator UI implies at least two operational roles:

- Borrower (limited scope)
- Officer (broader scope, can mutate pipeline and products)

Your current frontend role system is hardcoded demo credentials (fine for POC), but v2 needs:

- Server-side authorization for officer endpoints
- PII handling and retention
- Stronger audit logging (your system already has some audit hooks; this needs to expand to “operational actions”)

### 4.8 Architecture delta: where the UI design lives vs where your backend lives

The UI design in `/doc/02_Loan-Navigator-AI` currently includes:

- A Node/Express server and Postgres/Drizzle schema
- An OpenAI-driven chat response handler

Your actual product POC is:

- Python/FastAPI + LangGraph + XGBoost + MLflow

**Implication (practical):**

- The UI design is best treated as a **reference implementation for UI and data contracts**, not as the backend to adopt wholesale.
- The cleanest v2 move is:
  - Keep **Python** as the “brains” (agents, ML, policy guardrails, audit).
  - Implement the **Loan Navigator API contract** in FastAPI.
  - Port or recreate the UI in your main `frontend/` so it talks to FastAPI instead of the Node mock.

## 5. Concrete modifications required to “jump” from current POC to the target

This is the minimal set of changes that must exist before v2 can look/feel like the Loan Navigator design.

### 5.1 Frontend (product surfaces)

Minimum changes:

- Add routing and pages for:
  - Borrower chat
  - Officer dashboard
  - Pipeline
  - Officer lifecycle chat
  - Product catalog
- Implement the top “Phase tracker” for borrower journey as a first-class UI component (your current progress bar is close in spirit but not equivalent in meaning).
- Introduce consistent theming and layout primitives matching the Loan Navigator design.

### 5.2 Backend (API contract + persistence)

Minimum changes:

- Introduce persistence for:
  - conversations
  - messages (+ metadata)
  - phases
  - loans
  - product catalog
- Implement endpoints that mirror the Loan Navigator contract (even if initially backed by SQLite and simple logic).
- Ensure every “assistant response” can return:
  - plain text response
  - structured metadata used by UI panels (scores, blockers, recommended products, next actions)

### 5.3 Agent workflows (feature mapping)

Map each wow feature → the minimum backend artifacts needed:

1. Borrowing Strategy Designer
   - Product catalog present and queryable
   - Strategy output schema (loan splits, alternatives, reasons)
   - Recommendation cards UI output

2. Approval Probability Navigator
   - Probability score (can start from existing XGBoost probability)
   - Blockers extraction (rule-based at first; later policy+model-driven)
   - Next actions list (structured; with expected impact)

3. Autonomous Application Completion Agent
   - Document checklist per product + borrower type
   - Document submission state per loan
   - Mismatch detection rules (names, dates, addresses, account numbers)
   - Reminders/escalation scheduling

4. Explainable Underwriting Copilot
   - Underwriting memo schema (sections)
   - Link to policy context (RAG retrieval) and model evidence
   - Deterministic guardrails for “no promises / compliance-safe language”

5. Pipeline Rescue + Next-Best-Action Console
   - Pipeline state and per-loan “stuck reason”
   - Loan health score / abandonment likelihood heuristic
   - Daily action list generator (structured)

## 6. Suggested v2 sequencing (to minimize risk while staying faithful to the design)

This is an implementation-oriented sequence, not a timeline.

1. **Lock the data contracts (Conversation/Message/Loan/Phase/Product)**
   - Use the Loan Navigator `shared/schema.ts` as the conceptual contract baseline.

2. **Build the product API layer in FastAPI**
   - Implement `/api/conversations`, `/api/messages`, `/api/phases`, `/api/loans`, `/api/catalog-products`.

3. **Port the Loan Navigator UI into the real frontend**
   - Make the UI talk to FastAPI endpoints.
   - Keep “existing POC analysis panels” temporarily, but treat them as internal debug views.

4. **Implement “wow features” incrementally through structured metadata**
   - First: show stable panels with placeholder + rule-based values.
   - Then: drive them from the agent graph and model outputs.

5. **Replace rule-based logic with policy-aware + model-aware logic**
   - RAG policies + underwriting rules per territory/product.

## 7. Bottom line

The new documentation and UI design make sense and are coherent. The principal engineering challenge is not “LLM prompts” or “one more model”. It is introducing:

- A **workflow-first domain model** (conversations → loans → phases → documents → actions),
- An **API contract that supports those workflows**, and
- A **UI implementation that reflects borrower vs officer realities**.

Your current POC is a strong “brains demo” (agent + ML + MLOps). The target is a strong “product demo” (experience + operations). The jump is absolutely doable, but it requires treating persistence, workflows, and UI surfaces as the core of v2 rather than as add-ons.

