# KS LOS v2 — System Design (Loan Navigator)
**Version:** 2.0 (Design Baseline)  
**Audience:** Engineering, product, compliance, and delivery stakeholders  
**Style note:** This document is written in British English and adopts a scientific, audit-oriented tone.

---

## 1. Executive Summary

KS LOS v2 is a workflow-first **Loan Origination System** whose primary product surface is the Loan Navigator UI. Unlike the prior POC, which principally demonstrates model-centric decisioning, v2 is designed to operationalise lending: it converts borrower conversations into persisted artefacts (conversations, loans, phases, documents) and provides officers with an actionable workspace (dashboard, pipeline, lifecycle actions).

The architectural proposition is that AI is valuable when it is **contractual** (typed outputs), **grounded** (retrieval-backed), and **auditable** (traceable to inputs, sources, and model/tool versions). Accordingly, v2 pairs:

- A **product API** (FastAPI) exposing workflow entities and enforcing borrower/officer boundaries.
- An **agentic core** (LangGraph/LangChain) that produces structured outputs driving state transitions.
- A **knowledge base (RAG)** grounded in authoritative artefacts (policy, product, checklist, SOP), stored in PGVector.
- A **predictive scoring layer** (XGBoost) with reproducible experiment tracking (MLflow).
- **Banking-grade persistence and audit** (PostgreSQL + immutable audit events + correlation IDs).

This design defines the system at a “deep but general” level: components, interfaces, data standards, evaluation metrics, and operational constraints sufficient for rigorous implementation and review.

---

## 2. Scope, Goals, and Non-Goals

### 2.1 In Scope

- Borrower experience: persisted chat, phase tracker, recommendations, checklist-driven next steps.
- Officer experience: lead dashboard, loan pipeline board, officer lifecycle chat, product catalogue management.
- Agentic behaviour: structured outputs for intent analysis, recommendations, phase/loan actions, and underwriting artefacts.
- Grounded reasoning: policy- and product-aware RAG with measurable retrieval quality gates.
- Observability: correlation IDs, audit trails, metrics, and traceability from message to state change.

### 2.2 Design Goals (Quality Attributes)

| Attribute | Goal |
|---|---|
| Correctness | State transitions and decisions must be validated and reproducible. |
| Auditability | Every material state mutation is attributable to an actor and evidence. |
| Groundedness | Policy/product specifics must be supported by retrieved sources. |
| Safety | No promises of approval; constrained actions; robust refusal behaviour. |
| Testability | Deterministic seeds, stable fixtures, and repeatable evaluation. |
| Operational simplicity | Local-first runtime; staged migration to hardened infra. |

### 2.3 Out of Scope (for v2 baseline)

- Full production identity management (beyond planned RBAC upgrade path).
- Full document ingestion pipeline (OCR, identity checks) beyond baseline checklist/status tracking.
- Formal regulatory certification; this design proposes compliance-aligned controls rather than claiming compliance.

---

## 3. Technology Profile (Current + Target)

The implementation is intentionally pragmatic: local-first tooling for reproducibility, with a clear path to hardened, bank-grade deployment.

| Layer | Technology | Role |
|---|---|---|
| Frontend | React (Loan Navigator UI) | Product surface and behavioural contract. |
| API | FastAPI | Product API layer, RBAC boundary, persistence orchestration. |
| Agent orchestration | LangGraph / LangChain | Multi-step, tool-augmented reasoning with typed outputs. |
| LLM runtime | Ollama (local) | Local inference and privacy-first operation. |
| Default LLM | `qwen2.5:7b` | Cost-effective general reasoning; can be swapped by configuration. |
| Embeddings | `nomic-embed-text` via Ollama | Local embedding generation for RAG. |
| Relational database | PostgreSQL | Workflow entities, audit events, catalogue, and operational state. |
| Vector database | PGVector (Postgres extension) | RAG storage with structured metadata. |
| ML scoring | XGBoost | Predictive score/probability; used as evidence within decisions. |
| Experiment tracking | MLflow | Training/inference telemetry, model registry, drift linkage. |
| Observability | Prometheus, Grafana, OpenTelemetry | Metrics, dashboards, traces, and SLO tracking. |
| Test harness | Pytest, Playwright | Unit/integration verification and UI contract regression. |

---

## 4. High-Level System Architecture

### 4.1 Architecture Overview

The system is designed around a strict separation of concerns:

- **UI contract**: the Loan Navigator UI defines behavioural expectations and payload shapes.
- **Product API**: provides persistence, role boundary enforcement, and stable contracts.
- **Agentic core**: produces validated, typed outputs; triggers workflow actions.
- **Evidence sources**: catalogue, policies, SOPs, and checklists are the authority for “rules”.

### 4.2 High-Level Architecture Diagram

```mermaid
flowchart TB
  subgraph Clients
    B[Borrower UI<br/>Chat + Phase tracker + Recommendations]
    O[Officer UI<br/>Dashboard + Pipeline + Officer chat + Products]
  end

  subgraph "Product API Layer (FastAPI)"
    GW[HTTP API + OpenAPI<br/>Error envelopes + Correlation IDs]
    AUTH[Role boundary<br/>Borrower vs Officer<br/>RBAC upgrade path]
    ORCH[Workflow orchestration<br/>Persistence + idempotency]
  end

  subgraph "Agentic Core (LangGraph)"
    JC[Journey Coach<br/>conversation handling]
    TOOLS[Tool execution<br/>validated inputs/outputs]
    PARSE[Profile/Intent parsing<br/>typed schemas]
    RE[Risk/Policy synthesis<br/>RAG + model evidence]
    ADV[Advisory & next steps<br/>safe language]
  end

  subgraph "Data & Evidence Stores"
    PG[(PostgreSQL<br/>workflow entities + audit)]
    VEC[(PGVector<br/>RAG corpus: policies/products/SOP)]
    MLR[(MLflow tracking store<br/>runs + registry)]
  end

  subgraph "Local Model Runtime"
    LLM[LLM (Ollama)<br/>e.g., qwen2.5:7b]
    EMB[Embeddings (Ollama)<br/>nomic-embed-text]
    XGB[XGBoost scorer]
  end

  subgraph "Observability"
    MET[Prometheus metrics]
    TR[OpenTelemetry traces]
    AUD[Audit log events]
  end

  B -->|HTTPS| GW
  O -->|HTTPS| GW
  GW --> AUTH --> ORCH
  ORCH -->|invoke| JC
  ORCH -->|invoke| TOOLS
  ORCH -->|invoke| PARSE
  ORCH -->|invoke| RE
  ORCH -->|invoke| ADV
  JC --> LLM
  TOOLS --> LLM
  PARSE --> LLM
  RE --> LLM
  ADV --> LLM
  RE -->|retrieve| VEC
  ORCH --> PG
  ADV --> MLR
  GW --> MET
  GW --> TR
  ORCH --> AUD
  EMB --> VEC

```

### 4.3 Diagram Walkthrough (Node-by-Node)

The diagram expresses a request/decision flow in which the Product API orchestrates persistence and invokes the agentic core under strict boundary, audit, and observability controls:

- **B (Borrower UI)** and **O (Officer UI)** send user actions as HTTPS requests to **GW**.
- **GW (HTTP API + OpenAPI)** is the stable contract boundary: it validates requests, emits **MET** (metrics) and **TR** (traces), and forwards the call through **AUTH** to **ORCH**.
- **AUTH (Role boundary)** enforces borrower versus officer capabilities (and is the natural insertion point for full RBAC), ensuring that only authorised actions can reach workflow mutation paths.
- **ORCH (Workflow orchestration)** coordinates the unit of work: it loads and persists workflow state in **PG**, invokes agent steps as required, and emits immutable **AUD** events for every material write path.
- **JC (Journey Coach)** handles conversational turns and determines whether tool-assisted processing is required; it uses **LLM** for language understanding and response drafting.
- **TOOLS (Tool execution)** runs constrained tools (for example, structured profile generation) under validated inputs/outputs; it may use **LLM** when the tool is LLM-backed.
- **PARSE (Profile/Intent parsing)** converts tool output and dialogue context into typed objects; it may use **LLM** for extraction but must enforce schema validation.
- **RE (Risk/Policy synthesis)** retrieves authoritative context from **VEC** (the RAG corpus) and synthesises a decision rationale; in practice it may also incorporate predictive evidence (e.g., XGBoost) even when not explicitly drawn.
- **ADV (Advisory & next steps)** produces safe, user-facing guidance and logs relevant inference evidence to **MLR** for governance and reproducibility.
- **EMB (Embeddings)** writes new or updated corpus embeddings into **VEC**, separating “knowledge maintenance” from runtime orchestration.

---

## 5. Domain Model (Workflow-First)

v2 is designed around operational objects rather than “chat outputs”.

| Entity | Purpose | Notes (bank-grade expectations) |
|---|---|---|
| Conversation | Lead container for borrower interactions | Status, assignment, derived scores, audit trail. |
| Message | Immutable event log of dialogue | Includes metadata payloads consumed by UI panels. |
| LoanPhase | Ordered lifecycle stage definitions | Managed by officers; drives pipeline grouping. |
| Loan | Origination artefact that moves through phases | Stores required document checklist and statuses. |
| CatalogProduct | Product definitions, eligibility, required docs | Must be versioned and effective-dated. |
| AuditEvent | Immutable record of state mutations | Primary evidence trail for compliance and debugging. |

### 5.1 Proposed Persistence Schema (Logical)

The following logical tables are sufficient to support the Loan Navigator surfaces whilst remaining compatible with bank-grade integrity constraints.

| Table | Key fields (indicative) | Integrity and audit requirements |
|---|---|---|
| `conversations` | `id`, `status`, `chat_role`, `current_phase_id`, `created_at` | Status must be constrained; phase must be valid; write events audited. |
| `messages` | `id`, `conversation_id`, `role`, `content`, `metadata_json`, `created_at` | Append-only per conversation; metadata validated; PII policy enforced. |
| `loan_phases` | `id`, `name`, `order_index`, `is_active` | Order index unique; deactivation auditable; effective dating preferred. |
| `loans` | `id`, `conversation_id`, `phase_id`, `status`, `attributes_json` | Phase transitions constrained; officer-only mutations; full audit. |
| `catalog_products` | `id`, `name`, `eligibility_json`, `fees_json`, `effective_from/to` | Effective-dated; changes versioned; recommendations cite version. |
| `audit_events` | `id`, `entity_type`, `entity_id`, `actor_role`, `event_type`, `payload_json`, `correlation_id`, `created_at` | Append-only, immutable; must exist for each write path. |

---

## 6. Databases, Data Standards, and Banking-Grade Requirements

### 6.1 Relational Database Standards (PostgreSQL)

The database design must meet typical banking-grade constraints:

- **ACID transactions** for workflow mutations (loan/phase/product updates).
- **Referential integrity** via foreign keys; no orphaned workflow entities.
- **Strict constraints** (e.g., status enums, non-null invariants, check constraints for ranges).
- **Idempotency** for retry-safe endpoints (seed routines, action execution).
- **Immutable audit events** as append-only records, never overwritten.

### 6.2 Data Protection (Proposal)

- Encryption in transit (TLS) for API-to-DB connectivity in hardened environments.
- Encryption at rest for database volumes.
- Data minimisation: avoid storing unnecessary PII in retrieval systems.
- Retention policy: define retention windows for messages, inference logs, and audit events.

### 6.3 Data Contracts and Interoperability

- API payloads must be **schema-driven** (Pydantic + OpenAPI).
- Agent outputs must be **typed JSON** (validated) rather than free-form narrative.
- Where external standards apply (e.g., Metro 2), use adapters and validation gates.

---

## 7. Knowledge Base (RAG) Design

### 7.1 Purpose and Principle of Authority

RAG exists to prevent “policy invention” and to make decisions reviewable. The RAG corpus must be restricted to authoritative sources (policy, product catalogue, SOP, and document-checklist rules).

### 7.2 Current Implementation Baseline

- Vector store: PGVector (PostgreSQL).
- Collection name: `credit_policies`.
- Embedding model: `nomic-embed-text` (local via Ollama).
- Chunking (current default): 500 characters, 50 overlap, split by headings/newlines/spaces.

### 7.3 Corpus Composition (v2 Proposal)

| Corpus pack | Examples | Rationale |
|---|---|---|
| Policy | credit policy, exceptions, underwriting thresholds | Ground underwriting decisions and conditions. |
| Product | catalogue, eligibility, pricing, fees, effective dates | Prevent product hallucination; enable consistent recommendations. |
| Checklist/KYC | required document baseline, variants by product/segment | Drives autonomous completion and progress tracking. |
| SOP | officer lifecycle actions, escalation, rationale requirements | Makes operational actions safe and auditable. |

### 7.4 Retrieval and Quality Metrics (Proposed)

RAG quality must be measured and gated, not “felt”.

| Metric | Definition | Target (initial) |
|---|---|---|
| Hit-rate@k | % of golden questions where a relevant chunk is in top-k | ≥ 0.85 at k=5 |
| Citation correctness | % of answers whose cited sources contain the asserted rule | ≥ 0.90 |
| Unsupported-claim rate | % of answers asserting specifics without supporting citation | ≤ 0.05 |
| Retrieval latency | p95 time for vector retrieval | ≤ 150 ms (local) |
| End-to-end RAG latency | p95 retrieval + synthesis (excluding UI/network) | ≤ 2.0 s (POC budget) |

### 7.5 Chunking Strategy (Rationale and Future Options)

The current chunking (character-based) is a workable baseline. For higher precision, v2 should adopt **section-aware chunking**:

- Chunk by semantic sections (e.g., Markdown headings) to preserve policy boundaries.
- Attach metadata: `doc_type`, `jurisdiction`, `effective_date`, `version`, `section_path`.
- Apply retrieval filters (e.g., jurisdiction + effective date) before similarity search.

---

## 8. LLM Model Strategy (Local-First, Justified)

### 8.1 Selection Principles

Model choices must be justified by measurable requirements:

- **Determinism and schema reliability** for structured outputs.
- **Latency and throughput** appropriate for interactive workflows.
- **On-premise viability** (privacy, cost control, regulatory constraints).

### 8.2 Proposed Model Portfolio

| Task type | Recommended class | Candidate models (examples) | Justification |
|---|---|---|---|
| Structured extraction (intent, actions) | small/medium instruct model | Qwen2.5 7B (current default), Llama 3.x 8B | Lower latency; high schema adherence with proper prompting/validation. |
| Complex synthesis (underwriting memo) | larger reasoning model | Llama 3.x 70B (where infra allows) | Better long-form reasoning; improved citation discipline when constrained. |
| Embeddings | dedicated embedding model | `nomic-embed-text` | Strong retrieval quality; local-first with Ollama integration. |

The baseline implementation currently defaults to `qwen2.5:7b` and uses `nomic-embed-text` for embeddings. Both remain configurable by environment variables to support bank-specific constraints.

### 8.3 Safety and Constrained Generation

For banking workflows, the system must treat the LLM as an assistant, not an authority:

- LLM outputs must be validated (JSON schema and business rules).
- Operational actions (loan/phase/product mutation) must be explicitly authorised and recorded.
- Policy and product claims must be grounded in retrieved sources, or refused.

### 8.4 Decision Quality Metrics (Proposed)

v2 should treat both “LLM quality” and “credit decisioning quality” as measurable, testable properties.

| Metric class | Metric | Definition | Target (initial) |
|---|---|---|---|
| Predictive model accuracy | ROC-AUC | Discrimination of good vs bad outcomes | ≥ 0.75 (baseline) |
| Predictive model calibration | Brier score | Probability accuracy | ≤ 0.20 (baseline) |
| Threshold stability | PSI (population stability index) | Drift between training and inference cohorts | ≤ 0.10 (watch) |
| Fairness monitoring | Approval parity by territory | Relative approval rates across territories | Defined tolerance band |
| Agent output validity | Schema validity rate | % of agent outputs that validate without repair | ≥ 0.98 |
| Grounded decisioning | Supported decision rate | % of decisions citing relevant policy/product | ≥ 0.90 |

---

## 9. Agentic System Design

### 9.1 Current Agentic Graph (Implementation Baseline)

The existing agentic workflow is a LangGraph state machine with the following nodes:

1. Journey coach (conversation and tool-routing)
2. Tools (profile generation, etc.)
3. Profile parser (typed model validation)
4. Risk engine (RAG + XGBoost + LLM synthesis)
5. Advisory (safe recommendation text)

### 9.2 v2 Agent Set (Proposed Expansion)

We require specialised agents to support operational “wow features” and officer actions:

| Agent | Primary responsibility | Output (typed) |
|---|---|---|
| Intent & Lead Scoring | Extract intent summary, seriousness/fit scores, next angle | `IntentAnalysis` payload |
| Product Recommender | Select products from catalogue with reasons | `LoanRecommendations[]` |
| Phase Progression Controller | Suggest/validate phase updates (borrower sequential rules) | `PhaseAction` |
| Document Checklist Engine | Compute required docs and manage statuses | `DocumentChecklist` + status updates |
| Underwriting Memo Composer | Create underwriting artefact with citations | `UnderwritingMemo` |
| Officer Action Validator | Validate and execute officer lifecycle actions | `LoanAction` / `PhaseAdminAction` |
| Pipeline Analyst (NBA) | Prioritise cases and recommend next best actions | `NextBestActions[]` |

The baseline graph contains 5 nodes; the v2 proposal expands this to an operational set of 7 specialised agents (with the option to merge roles where latency or complexity requires).

### 9.3 Agentic Workflow Diagram (Conceptual)

```mermaid
flowchart LR
  U[User message] --> INT[Intent & scoring]
  INT --> REC[Product recommender]
  REC --> PH[Phase progression]
  PH --> DOC[Checklist engine]
  DOC --> UW[Underwriting memo (officer view)]
  UW --> NBA[Pipeline analyst]
  NBA --> OUT[Structured outputs + UI surfaces]

  REC -->|catalog queries| CAT[(Catalog products)]
  DOC -->|rules retrieval| KB[(RAG corpus)]
  UW -->|policy citations| KB
  PH -->|state validation| DB[(Workflow DB)]
  OUT --> DB
```

### 9.4 Visualisation of the Agentic Workflow (Step Table)

| Step | Node/Agent | Input | Operation | Output |
|---|---|---|---|---|
| 1 | Intent & scoring | Message + conversation context | Typed extraction, normalisation | Scores, intent summary |
| 2 | Recommendations | Intent + catalogue | Constraint-based selection | Recommended products |
| 3 | Phase controller | Current phase + rules | Validate sequential progression | Phase updates |
| 4 | Checklist engine | Product + borrower segment | Generate checklist, update statuses | Required docs + status |
| 5 | Underwriting memo | Profile + policy + evidence | Structured synthesis with citations | Underwriting memo |
| 6 | Pipeline analyst | Portfolio + statuses | Prioritisation and interventions | Next-best actions |

### 9.5 Agentic Code Structure (Implementation Baseline)

The current codebase expresses the agentic core as a LangGraph workflow with clearly separated concerns:

```text
src/
  agents/
    graph.py        (LangGraph graph assembly and routing)
    nodes.py        (node implementations: journey, parsing, risk, advisory)
    prompts.py      (system prompts and prompt builders)
    tools.py        (tool definitions invoked by the LLM)
    state.py        (AgentState schema for graph state)
  api/
    routers/
      agent_router.py  (HTTP interface for graph invocation; Phase 2 POC)
```

The baseline workflow composition is defined in [graph.py](file:///Users/albertohernandez/Documents/projects/ks-los/src/agents/graph.py) and node implementations are in [nodes.py](file:///Users/albertohernandez/Documents/projects/ks-los/src/agents/nodes.py). The v2 design principle is that every proposed agent maps to either:

- a new node in the graph, or
- a constrained tool with typed inputs and typed outputs, executed under the same audit and traceability conventions.

---

## 10. Protocols, Conventions, and Operational Contracts

### 10.1 API Conventions

- RESTful JSON APIs with OpenAPI contracts.
- Consistent error envelopes with correlation identifiers.
- Idempotent endpoints for retry-safe operations (seed routines; action execution).

### 10.2 Traceability Conventions

- `X-Correlation-ID` propagated across write paths.
- W3C `traceparent` where tracing is enabled.
- Audit events record: actor role, entity IDs, validated payload, and outcome.

---

## 11. Regulations and Compliance (Proposal)

This design does not claim regulatory compliance; it proposes controls aligned with typical banking expectations:

- **KYC/AML**: checklist-driven verification steps and auditable completion records.
- **Credit reporting**: where Metro 2 is used, ensure strict formatting and validation gates.
- **Data protection**: retention, minimisation, and access control by role.
- **Model governance**: tracked model versions (MLflow) and drift monitoring inputs.

---

## 12. Observability and Scientific Rigor

### 12.1 Proposed SLIs (Initial)

| SLI | Definition | Target (POC) |
|---|---|---|
| Availability | % successful responses for critical endpoints | ≥ 99% (local demo) |
| Latency | p95 for borrower message send | ≤ 2.0 s (excluding warm-up) |
| Retrieval quality | citation correctness on golden set | ≥ 0.90 |
| Action safety | unauthorised mutation attempts blocked | 100% blocked |

### 12.2 Evidence Artefacts

For each phase, evidence must include:

- test outputs (unit/integration/e2e)
- validation report with explicit pass/fail statements
- trace/audit evidence for key write paths

---

## 13. Extensibility and Future-Proofing

v2 is designed to evolve without destabilising the UI contract:

- New products, policies, and SOPs can be added by corpus ingestion and catalogue updates.
- Model upgrades are supported by configuration and registry-driven deployment patterns.
- New jurisdictions can be introduced via metadata, policy packs, and retrieval filtering.
- Additional “agents” can be introduced by extending the agent graph whilst maintaining output schemas.

---

## 14. Key Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Hallucinated policy/product claims | Compliance and trust failure | Enforce citations; refuse when unsupported; golden-set gates. |
| Schema drift in agent outputs | UI breakage | Versioned schemas; regression tests; compatibility policy. |
| Non-deterministic demos/tests | Delivery risk | Deterministic seeding; stable fixtures; controlled randomness. |
| PII exposure via RAG | Data protection risk | Metadata discipline; avoid embedding sensitive identifiers; access controls. |

---

## 15. Implementation Roadmap (Anchored to v2 Plan)

This document complements (but does not replace) the chronological control plan:

- Master execution plan: `/doc/02_v2/03_planning.md`
- Work packages: `/doc/02_v2/02_work_packages.md`
- Acceptance gates: `/doc/02_v2/acceptance.md`
