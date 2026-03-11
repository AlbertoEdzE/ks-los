# Project Ontology Definition (LOS v2)

**Document ID:** ONT-V2-001  
**Version:** 1.0  
**Phase:** 0.1  
**Status:** Draft  
**Last Updated:** March 2026

---

## 1. Purpose and Scope

This document establishes the authoritative ontology for **KS LOS v2** (Loan Navigator). It defines the system taxonomy, bounded contexts, core entities, and the input/output contracts required to implement the UI design in `/doc/02_Loan-Navigator-AI` as a functional end-to-end application.

This ontology is the source of truth for v2 implementation decisions. Any divergence from it requires an explicit architectural decision recorded in the v2 architecture documentation.

**Source of Truth (UI + implied API contracts):**  
[/doc/02_Loan-Navigator-AI](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI)

---

## 2. System Overview

### 2.1 Product Surfaces (Must Match Design)

The system consists of the following user-facing surfaces defined by the Loan Navigator UI:

- Borrower Chat (`/`) with phase tracker and recommendation experience  
  Reference: [chat.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/chat.tsx)
- Officer Dashboard (`/dashboard`) showing lead list, scores, and detail  
  Reference: [officer-dashboard.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/officer-dashboard.tsx)
- Loan Pipeline (`/pipeline`) as a phase-based board of loan artifacts  
  Reference: [loan-pipeline.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/loan-pipeline.tsx)
- Loan Product Catalog (`/loan-products`) management experience  
  Reference: [loan-products.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/loan-products.tsx)
- Officer Lifecycle Chat (`/officer-chat`) for operational actions via chat  
  Reference: [officer-chat.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/officer-chat.tsx)

### 2.2 Core Conceptual Model

The v2 system is workflow-first and is centered around:

- **Conversation**: a lead container and workflow state object
- **Loan**: an operational artifact created/updated by officers (linked to conversation when relevant)
- **Phase**: ordered lifecycle stages used for both borrower journey visibility and pipeline processing
- **Catalog Product**: configured lending products with constraints and required documents
- **Message**: the immutable event log of interaction (plus metadata payloads)

This conceptual model is explicitly represented in the Loan Navigator schema:
Reference: [schema.ts](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/shared/schema.ts)

---

## 3. Bounded Contexts

### 3.1 Borrower Experience Context

**Responsibility:** guide borrower intent capture, eligibility guidance, and progression through phases.

**Primary invariants:**
- Borrower cannot mutate officer-only resources.
- Borrower phase advancement is sequential and validated.

**Primary outputs:**
- Natural language assistant response.
- Structured metadata: intent summary, recommended products, phase updates.

### 3.2 Officer Operations Context

**Responsibility:** convert leads into loans, manage pipeline, and execute lifecycle actions.

**Primary invariants:**
- Officer actions must be authorized and fully auditable.
- Loan and phase mutations must preserve ordering and referential integrity.

**Primary outputs:**
- Loan creation/update events.
- Conversation assignment/status changes.
- Phase management actions (add/reorder/deactivate/reactivate).

### 3.3 Catalog and Policy Context

**Responsibility:** maintain product catalog (constraints, eligibility, required documents, features).

**Primary invariants:**
- Products have stable codes and versioned changes (audit requirement).
- Eligibility criteria must be machine-interpretable (initially rules/strings, later structured).

### 3.4 Decisioning and Explainability Context

**Responsibility:** produce approval likelihood, blockers, next best actions, and underwriting artifacts.

**Primary invariants:**
- Outputs must be supported by evidence (catalog constraints, borrower data, policy fragments, model factors).
- Guardrails prevent promises and disallowed claims.

### 3.5 Workflow Automation Context

**Responsibility:** document checklist, reminders/escalations, exception detection, time-in-stage tracking.

**Primary invariants:**
- Every automated action is recorded as an audit event.
- Timers and scheduled tasks must be idempotent and safe to retry.

---

## 4. Core Entities (v2 Data Dictionary)

The following entities are mandatory and must map to the UI schema definitions.

### 4.1 Conversation

Key fields (conceptual):
- `id`
- `borrowerName`
- `status` (active/reviewing/qualified/archived)
- `chatRole` (borrower/officer)
- `currentPhaseId`
- `seriousnessScore`, `fitScore`
- `intentSummary` (JSON)
- `recommendedProducts` (JSON)
- `nextConversationAngle`
- `assignedOfficer`

### 4.2 Message

Key fields (conceptual):
- `conversationId`
- `role` (user/assistant)
- `content`
- `metadata` (JSON payload for extracted intent, recommendations, actions, audits)

### 4.3 LoanPhase

Key fields (conceptual):
- `name`, `description`
- `sortOrder`, `isActive`
- `color`, `icon`

### 4.4 Loan

Key fields (conceptual):
- borrower identity fields (name/email/phone)
- loan terms fields (type, amount, rate, tenure, emi)
- underwriting fields (income, debts, score, collateral, LTV)
- lifecycle fields (`currentPhaseId`, `status`, notes)
- linkage (`conversationId`, `createdBy`)

### 4.5 CatalogProduct

Key fields (conceptual):
- `name`, `code`, `category`, `status`
- constraints (amount range, tenure range, rates, fees)
- rules (minCreditScore, maxLTV, minIncome, collateralRequired)
- arrays (requiredDocuments, eligibilityCriteria, features)

---

## 5. Roles and Authorization Model (POC v2)

The UI design assumes two roles:

- **Borrower:** may create conversations and send messages in borrower mode.
- **Officer:** may list/manage conversations, loans, phases, and catalog products.

For the POC, officer authorization may use a header token boundary compatible with the Loan Navigator reference server implementation:
Reference: [routes.ts](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/server/routes.ts)

---

## 6. Contract Expectations (API + Structured Assistant Output)

### 6.1 API Contract Requirements

The backend must expose endpoints consumed by the UI, at minimum:
- Conversations and messages endpoints
- Phases endpoints
- Loans endpoints
- Catalog products endpoints

These are specified in detail in:
[/doc/02_v2/05_new_architecture/api_specifications.md](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_v2/05_new_architecture/api_specifications.md)

### 6.2 Structured Output Requirements

Assistant responses must support:
- `intentSummary` updates
- seriousness/fit scoring
- `recommendedProducts` payloads
- optional action payloads for officer role (phase actions, loan actions)

All structured outputs must be validated and stored as message metadata and/or conversation fields.

