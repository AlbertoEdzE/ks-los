# Technical Architecture (LOS v2)

## Overview

LOS v2 implements the Loan Navigator UI as the product surface and builds a backend that makes it a functional application. The UI is the behavioral contract; the backend is responsible for persistence, workflow state, structured assistant outputs, and role-based access.

**Source of Truth (UI + implied data contracts):**  
[/doc/02_Loan-Navigator-AI](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI)

---

## 1. Architecture Goals

- Enable borrower and officer experiences exactly as specified by the UI design.
- Persist workflow-first domain objects: conversations, messages, phases, loans, catalog products.
- Provide agentic behaviors via validated structured outputs (metadata) rather than brittle UI parsing.
- Ensure all state changes are auditable and attributable to actor role and correlation ID.

---

## 2. System Components

### 2.1 Frontend (Loan Navigator UI)

The v2 frontend must replicate the design implementation in:

- Borrower Chat: [chat.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/chat.tsx)
- Officer Dashboard: [officer-dashboard.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/officer-dashboard.tsx)
- Pipeline: [loan-pipeline.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/loan-pipeline.tsx)
- Products: [loan-products.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/loan-products.tsx)

The frontend calls the product API endpoints defined in:
[/doc/02_v2/05_new_architecture/api_specifications.md](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_v2/05_new_architecture/api_specifications.md)

### 2.2 Backend (Product API + Workflow State)

The backend responsibilities:

- Implement the UI-consumed endpoints for conversations/messages/phases/loans/catalog products
- Enforce authorization boundaries for borrower vs officer actions
- Generate and store structured assistant metadata (intent, scores, recommendations, actions)
- Provide audit events and correlation IDs for every write

### 2.3 Persistence Layer

The persistence layer must support:

- Conversations, messages, loan phases, loans, loan product catalog

The conceptual schema should map to the entities defined by:
[schema.ts](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/shared/schema.ts)

### 2.4 Agent Core (Structured Output Engine)

The agent core is responsible for producing:

- Borrower intent summary
- Seriousness and fit scores
- Recommended products (from catalog + borrower intent)
- Phase update suggestions (validated sequentially for borrower)
- Officer-only actions (phase actions, loan actions) with validation and audit records

Agent outputs must be:

- Typed and validated (schema enforcement)
- Stored (message metadata and/or conversation fields)
- Deterministic where required (e.g., rules, guardrails)

---

## 3. Data Flow (High-Level)

### 3.1 Borrower Chat Flow

1. Borrower creates a conversation.
2. Borrower sends a message.
3. Backend appends user message and runs assistant engine.
4. Backend stores assistant message + metadata.
5. Backend may update conversation fields (intent summary, scores, current phase, recommended products).

### 3.2 Officer Workflow Flow

1. Officer lists conversations and selects a lead.
2. Officer may update conversation status/assignment.
3. Officer may create or patch loans and move them through phases.
4. Officer lifecycle chat may emit actions that mutate phases or loans.

---

## 4. Non-Functional Requirements

- Reliability: all writes must be idempotent where feasible and safe to retry.
- Auditability: every state mutation has an audit record.
- Security: borrower cannot access officer resources; officer actions must be authenticated.
- Testability: deterministic seeds for phases/products and stable test fixtures for E2E.

