# KS LOS v2 – Acceptance Guide (Loan Navigator UI)

## Scope

- Verify borrower and officer user journeys as implemented by the Loan Navigator UI design.
- Verify the product API contract and persistence for conversations, phases, loans, and catalog products.
- Verify agentic metadata surfaces (scores, intent summary, recommendations, actions) are stable and auditable.

## Source of Truth

- UI + expected behaviors: [/doc/02_Loan-Navigator-AI](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI)

## Acceptance Gates (Required)

- All Phase exit criteria satisfied (see [/doc/02_v2/03_planning.md](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_v2/03_planning.md))
- Unit test suite passes
- Integration test suite passes
- Playwright E2E suite passes and report is saved
- Validation report is written for the phase under `/doc/02_v2/04_documentation/phase_<N>/`

## Performance Budgets (POC v2)

- Borrower message send: p95 ≤ 2.0s backend processing time (excluding model warmup)
- Officer dashboard refresh: p95 ≤ 400ms for `/api/conversations` with demo data
- Pipeline render: p95 ≤ 500ms for `/api/loans` with demo data
- UI should remain responsive during loading (no blocking main thread tasks)

## End-to-End Acceptance Flows

### 1) Borrower Flow (Chat + Phases + Recommendations)

1. Open borrower chat page (`/`).
2. Start a conversation from the welcome state.
3. Send a message; verify:
   - A conversation is created and messages persist on refresh.
   - The phase tracker renders (when active phases exist).
4. Continue the chat; verify:
   - The conversation gains structured metadata (intent summary, seriousness/fit).
   - Recommended products are produced and persisted (if applicable).
5. Refresh the page; verify:
   - The conversation can be resumed and the UI state is consistent.

### 2) Officer Flow (Dashboard + Lead Detail)

1. Navigate to Officer Dashboard (`/dashboard`).
2. Verify:
   - Conversations list loads.
   - Scores (seriousness/fit) appear when present.
3. Select a conversation and verify:
   - Message history appears.
   - Intent summary and next conversation angle appear when present.
4. Update conversation status and assignment (if supported); verify persistence.

### 3) Officer Flow (Loan Pipeline)

1. Navigate to Pipeline (`/pipeline`).
2. Verify:
   - Phases are loaded and ordered.
   - Loans are grouped by `currentPhaseId`.
3. Open a loan; update fields; verify:
   - PATCH is accepted.
   - The pipeline UI reflects the update on refresh.

### 4) Officer Flow (Product Catalog)

1. Navigate to Products (`/loan-products`).
2. Verify:
   - Products list loads.
   - Create product works (draft).
   - Edit product persists.
   - Status transitions are reflected in UI and API.

## Audit and Correlation IDs

- Every API response should include or accept a correlation identifier, and the backend should record:
  - event name, endpoint, status, actor role, entity IDs (conversation/loan/product), and timestamp
- Every “assistant action” that mutates state should emit an audit record with:
  - action type, validated payload, and resulting state change

## Artefacts

- Playwright HTML report: `e2e/playwright-report/`
- Phase validation reports: `/doc/02_v2/04_documentation/phase_<N>/validation_report.md`
- Phase test reports: `/doc/02_v2/04_documentation/phase_<N>/test_report.md`
- Phase integration notes: `/doc/02_v2/04_documentation/phase_<N>/integration_notes.md`

