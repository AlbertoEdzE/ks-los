# Issue Tracking Setup (LOS v2)

**Document ID:** JIRA-V2-001  
**Version:** 1.0  
**Phase:** 0.4  
**Status:** Draft  
**Last Updated:** March 2026

---

## 1. Purpose and Scope

This document defines the issue tracking workflow for KS LOS v2. The issue tracker is the operational backbone for coordinating work packages across frontend, backend, data/persistence, agent core, and E2E testing with explicit dependencies and acceptance criteria.

The v2 issue tracking model must mirror the Work Breakdown Structure:
[/doc/02_v2/04_documentation/02_work-breakdown-structure.md](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_v2/04_documentation/02_work-breakdown-structure.md)

---

## 2. Project Structure

### 2.1 Epics

Create one Epic per phase:

- Phase 0: Foundation
- Phase 1: UI + API Skeleton
- Phase 2: Borrower Workflow
- Phase 3: Officer Workflow
- Phase 4: Agentic Features
- Phase 5: Hardening

### 2.2 Stories

Stories should map directly to:

- A UI route requirement from `/doc/02_Loan-Navigator-AI/client/src/pages`
- An API contract requirement consumed by the UI
- A persistence/migration deliverable
- A Playwright E2E scenario

---

## 3. Issue Types and Workflows

Use:

- Epic
- Story
- Task
- Bug
- Subtask

Recommended statuses:

- To Do → In Progress → In Review → Done
- Blocked (for tasks with explicit dependencies)

---

## 4. Required Fields

All Stories and Tasks must include:

- **Work Package ID:** `WP-V2-XXX`
- **Domain:** frontend / backend / data / agent / e2e / infra
- **Acceptance Criteria:** explicit, testable statements
- **Test Evidence:** which tests prove completion (unit/integration/e2e)
- **Dependencies:** upstream work items required

---

## 5. Ticket Templates

### 5.1 Story Template

```
Summary:
[Domain] <capability>

Context:
Link the UI source-of-truth page(s) and describe the expected behavior.

Acceptance Criteria:
- [ ] ...
- [ ] ...

API Contract:
- Endpoint(s):
- Request/response payload(s):

Data/Schema Impact:
- Tables/fields:
- Migration notes:

Testing:
- Unit:
- Integration:
- E2E (Playwright):

Dependencies:
- Blocks:
- Blocked by:
```

### 5.2 Bug Template

```
Summary:
<what fails>

Steps to Reproduce:
1)
2)

Expected:
...

Actual:
...

Suspected Root Cause:
...

Fix Notes:
...

Regression Test:
- [ ] Added/updated test coverage
```

---

## 6. Traceability Rules

- Every PR must link to at least one `WP-V2-XXX` issue.
- Every phase must end with:
  - a test report
  - a validation report
  - an updated acceptance checklist

