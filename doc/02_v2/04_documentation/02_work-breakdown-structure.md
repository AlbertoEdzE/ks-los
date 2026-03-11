# Work Breakdown Structure (LOS v2)

**Document ID:** WBS-V2-001  
**Version:** 1.0  
**Phase:** 0.2  
**Status:** Draft  
**Last Updated:** March 2026

---

## 1. Purpose and Scope

This document defines the formal Work Breakdown Structure (WBS) for **KS LOS v2**. The WBS decomposes the v2 goal—implementing the Loan Navigator UI as a fully functional system—into phase-aligned work packages with explicit deliverables, test artifacts, and acceptance gates.

**Source of Truth (UI + implied contracts):**  
[/doc/02_Loan-Navigator-AI](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI)

---

## 2. WBS Overview

### 2.1 Level 1: Project Phases

| Phase | Name | Objective |
|------:|------|-----------|
| 0 | Foundation | Freeze ontology, WBS, repo practices, issue tracking, contracts |
| 1 | UI + API Skeleton | Design-exact UI routes + contract-complete backend skeleton |
| 2 | Borrower Workflow | Chat persistence, phase progression, recommendations metadata |
| 3 | Officer Workflow | Dashboard, pipeline, lifecycle actions with auditability |
| 4 | Agentic Features | Probability navigator, completion agent, underwriting copilot |
| 5 | Hardening | Security, observability, regression suite, release acceptance |

Each phase produces:
- Implementation increments
- A test report
- A validation report
- (where applicable) an E2E Playwright report

---

## 3. Level 2: Phase Milestones and Deliverables

### 3.1 Phase 0: Foundation

#### 0.1 Ontology Definition
- Deliverable: `ONT-V2-001`
- Completion criteria: ontology reviewed, roles defined, entity dictionary frozen

#### 0.2 WBS Definition
- Deliverable: `WBS-V2-001`
- Completion criteria: deliverables + acceptance gates mapped for all phases

#### 0.3 Version Control Setup
- Deliverable: `VCS-V2-001`
- Completion criteria: branch rules and CI quality gates defined

#### 0.4 Issue Tracking Setup
- Deliverable: `JIRA-V2-001`
- Completion criteria: epics/stories templates align to WBS and UI routes

### 3.2 Phase 1: UI + API Skeleton

#### 1.1 Frontend route parity
- Deliverables:
  - Borrower chat page implemented as in Loan Navigator UI
  - Officer dashboard, pipeline, products, officer chat pages present
  - Shared layout/theme parity (dark mode and navigation)

#### 1.2 Backend contract parity
- Deliverables:
  - `/api/conversations` endpoints required by UI
  - `/api/phases` endpoints required by UI
  - `/api/loans` endpoints required by UI
  - `/api/catalog-products` endpoints required by UI
  - officer authorization boundary enforced

#### 1.3 Persistence baseline
- Deliverables:
  - DB schema and migrations for v2 entities
  - seed for loan phases and demo products
  - idempotent seed entry points

#### 1.4 Test and validation artifacts
- Deliverables:
  - Phase 1 test report
  - Phase 1 validation report
  - Phase 1 integration notes
  - Phase 1 E2E report (smoke coverage)

### 3.3 Phase 2: Borrower Workflow

- Deliverables:
  - conversation metadata enrichment (intent, scores)
  - phase progression logic consistent with UI tracker
  - product recommendation payloads derived from catalog
  - tests + E2E borrower flow report

### 3.4 Phase 3: Officer Workflow

- Deliverables:
  - dashboard lead scoring surfaces and detail view are functional
  - pipeline shows loan artifacts by phases and supports patch operations
  - officer chat can trigger lifecycle actions in a validated way
  - tests + E2E officer flow report

### 3.5 Phase 4: Agentic Features

- Deliverables:
  - approval probability navigator outputs and persistence
  - checklist + document completion workflow baseline
  - underwriting memo artifact with guardrails
  - validation and regression artifacts for agent outputs

### 3.6 Phase 5: Hardening

- Deliverables:
  - stronger auth (RBAC), retention policies, prompt hardening
  - observability dashboards and actionable metrics
  - stable regression suite + release acceptance script

---

## 4. Level 3: Deliverables → Test Artifacts Mapping

All deliverables must be tied to a test artifact category:

- **Unit tests:** schema validation, deterministic rules, transition guards
- **Integration tests:** API contract, persistence, authorization checks
- **E2E tests (Playwright):** UI flows for borrower and officer surfaces
- **Validation reports:** evidence that requirements match UI and contracts

---

## 5. Dependencies and Critical Path

The critical path is contract-first:

1. Freeze entity dictionary + API surface (Phase 0)
2. Achieve UI route parity and API skeleton parity (Phase 1)
3. Add borrower workflow semantics (Phase 2)
4. Add officer operational semantics (Phase 3)

Agentic features (Phase 4) depend on stable workflow state and persistence from phases 1–3.

