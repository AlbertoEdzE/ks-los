# UI2 Alignment Plan (New Source-of-Truth: Loan-Navigator-AI)

**Project:** KS LOS (LoanAssist AI)  
**Document:** 09_planing_ui2.md  
**Goal:** Align the current KS LOS codebase to match the behavior, workflows, and UI contract implemented in the new source-of-truth codebase at `/Users/albertohernandez/Documents/projects/Loan-Navigator-AI`.

---

## 1) Source-of-Truth: What “Done” Means

The target behavior is defined by the implementation (not screenshots) in the following Loan-Navigator-AI files:

- Borrower experience and flow: [borrower-home.tsx](file:///Users/albertohernandez/Documents/projects/Loan-Navigator-AI/client/src/pages/borrower-home.tsx)
- Chat bubble rendering + rich workflow cards (STP, affordability, terms acceptance + signature): [chat-bubble.tsx](file:///Users/albertohernandez/Documents/projects/Loan-Navigator-AI/client/src/components/chat/chat-bubble.tsx)
- Document workflow (categorized checklist + upload/delete + progress): [document-upload-panel.tsx](file:///Users/albertohernandez/Documents/projects/Loan-Navigator-AI/client/src/components/documents/document-upload-panel.tsx)
- Document API and storage (multer upload + per-loan document list + download + delete): [routes.ts](file:///Users/albertohernandez/Documents/projects/Loan-Navigator-AI/server/routes.ts#L1384-L1540)
- Terms acceptance API (accept + signature + trigger disbursement): [routes.ts accept-terms](file:///Users/albertohernandez/Documents/projects/Loan-Navigator-AI/server/routes.ts#L2021-L2078)

Functional “done” characteristics:

- Borrower UI supports a home→chat transition with an attachment/paperclip affordance, rich message cards, and a live journey tracker.
- Documents are a first-class workflow: categorized by loanType + employmentType, each doc type has status, and the borrower can upload and see progress.
- STP processing exists as an explicit workflow: status, steps/audit, and gating toward acceptance/disbursement.
- Offer acceptance includes: terms display, an acceptance checkbox, an in-chat signature canvas, and an API call that results in a disbursement confirmation.
- Officer capabilities exist for monitoring pipeline, reviewing documents, and operating the lifecycle.

---

## 2) Current KS LOS Status (Measured from the Repository)

### 2.1 Frontend (Current)

- The app is currently a React Router SPA with borrower and officer routes implemented inside [App.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/frontend/src/App.tsx).
- The borrower experience is centered around [ChatInterface.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/frontend/src/components/ChatInterface.tsx), which already includes:
  - Persisted conversation bootstrap, message send, and history loading
  - A borrower document upload panel driven by `loan.documentChecklist`
  - A footer-based signature canvas upload
- The borrower shell already includes a phase progress tracker and “Insights” side panel in [App.tsx BorrowerHomePage](file:///Users/albertohernandez/Documents/projects/ks-los/frontend/src/App.tsx#L223-L560).

### 2.2 Backend (Current)

- Conversations + borrower chat endpoints exist in [v2_conversations_router.py](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/v2_conversations_router.py) including:
  - Create conversation, list messages, send messages, load loan: [loan endpoint](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/v2_conversations_router.py#L1627-L1669)
  - Document upload with file persistence + OCR/PDF extraction preview: [documents/upload](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/v2_conversations_router.py#L1676-L1778)
  - Signature upload: [signature](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/v2_conversations_router.py#L1780-L1861)
- Loan checklist mechanics and extraction helpers exist in [v2_loans_router.py](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/v2_loans_router.py#L57-L137).
- Phase taxonomy exists (including pre-disbursement/disbursement as labels), but there is no STP engine, acceptance flow, or disbursement execution logic in the backend codebase (search for “stp/disburse/accept-terms” yields only phase text definitions).

---

## 3) Critical Gaps (KS LOS → Loan-Navigator-AI)

### 3.1 API Contract Gaps

- Missing `/api/documents/*` contract:
  - KS LOS currently stores uploads into `loan.document_checklist` items, but does not expose a `LoanDocument` list endpoint compatible with the source-of-truth contract.
- Missing `/api/loans/:id/accept-terms`:
  - KS LOS can upload signature as a file, but does not implement acceptance gating, terms state, or disbursement confirmation.
- Authentication model mismatch:
  - Loan-Navigator-AI relies on `requireAuth`/`requireOfficer` style auth (cookie/session). KS LOS uses header-based tokens / dev tokens (RBAC gate in [v2_auth.py](file:///Users/albertohernandez/Documents/projects/ks-los/src/api/routers/v2_auth.py)).

### 3.2 Frontend Behavior and UI Gaps

- Rich “card-in-chat” rendering:
  - KS LOS currently renders assistant messages as markdown only; Loan-Navigator-AI renders structured cards (bureau pull, affordability, STP progress, offer acceptance, disbursement confirmation) within chat bubbles.
- Document workflow UX parity:
  - KS LOS borrower document UX is checklist-driven and flat; Loan-Navigator-AI uses categories + types and a progress model tied to loanType/employmentType.
- Terms acceptance UX:
  - KS LOS signature is footer-based and does not include terms display + acceptance checkbox + accept/disburse button integrated into the chat flow.

---

## 4) Alignment Strategy (Scientific/Contract-Driven)

### Strategy Decision

Implement a **compatibility layer** in KS LOS so that:

- KS LOS can keep its existing `/api/conversations/*` and `/api/loans/*` endpoints for internal workflows, while
- adding source-of-truth compatible endpoints (`/api/documents/*`, `/api/loans/:id/accept-terms`) to enable UI parity and reduce translation logic.

This minimizes risk by avoiding an all-at-once rewrite, while still converging on the source-of-truth contract.

---

## 5) Work Plan (Phased, with Acceptance Gates)

### Phase A — API Contract Parity (Documents + Acceptance)

- [ ] Add document persistence model aligned to Loan-Navigator-AI:
  - Store: `loanId`, `userId/actor`, `category`, `documentType`, `status`, `reviewNote`, `fileName`, `originalName`, `mimeType`, `fileSize`, `filePath`, timestamps.
- [ ] Implement `/api/documents/upload` with:
  - Multipart upload, server-side file persistence, allowed mime types, size limit.
  - Create a document record and return a sanitized document object.
- [ ] Implement `/api/documents/loan/:loanId` (borrower: only own loan; officer: any loan).
- [ ] Implement `/api/documents/:id/download` and `/api/documents/:id` DELETE (with “cannot delete approved” guard).
- [ ] Implement `/api/loans/:id/accept-terms`:
  - Input: `signature` (dataURL) consistent with source-of-truth.
  - Persist acceptance: acceptedAt, signature artifact, offer snapshot, and status transition.
  - Return: `{ success, disbursement }` payload compatible with UI cards.

**Acceptance gate**
- [ ] Contract tests prove endpoint shapes match Loan-Navigator-AI behavior (happy path + auth failures + invalid payloads).

### Phase B — Borrower UI2 Parity (Chat + Cards + Attachments)

- [ ] Introduce a structured “message metadata → card renderer” layer:
  - Render message content plus optional workflow cards (STP, affordability, terms acceptance, etc.).
- [ ] Implement paperclip/attachment UX similar to borrower-home:
  - Attachment selection is distinct from “send message”; uploads should map to document endpoints.
- [ ] Replace the footer signature canvas with an in-chat “TermsAcceptanceCard” equivalent:
  - Terms list, acceptance checkbox, signature canvas, submit button calling `/api/loans/:id/accept-terms`.
- [ ] Ensure journey tracker reflects phase transitions and is consistent with source-of-truth phase naming/order.

**Acceptance gate**
- [ ] E2E tests: borrower can (1) chat, (2) upload required documents, (3) see progress, (4) accept terms + sign, (5) see disbursement confirmation.

### Phase C — Document Workflow UX2 (Categorized Checklist)

- [ ] Implement the “document categories” rules:
  - Input drivers: `loanType`, `employmentType`
  - Output: categories and required/optional types (identity, income salaried/self-employed, property/vehicle).
- [ ] Update borrower doc UI to show:
  - Category sections, per-type upload, per-type status badge, per-loan progress.
- [ ] Update officer doc UI to support:
  - Review statuses (approved/rejected/needs_reupload) and review notes.

**Acceptance gate**
- [ ] Unit tests: category rules, required-doc computation, and progress percent are deterministic.
- [ ] Integration tests: doc status updates roundtrip to the backend.

### Phase D — STP Processing + Disbursement Workflow

- [ ] Add an STP processor module equivalent in responsibility to Loan-Navigator-AI:
  - Steps, audit, gating conditions, and a “stop before disbursement” mode.
- [ ] Wire STP status into borrower chat cards:
  - Pre-disbursement checks, final checks, and “ready to accept” gating.
- [ ] Implement disbursement simulation output:
  - Reference number, amount/currency, date, method, account info.

**Acceptance gate**
- [ ] Integration tests: loan moves through phases based on STP completion, then accept-terms triggers disbursement output.

### Phase E — Auth + Security Convergence

- [ ] Decide and implement a single auth model that supports both borrower and officer:
  - Option 1: keep header-based tokens but add borrower identities and session-like scoping.
  - Option 2: implement cookie/session auth like source-of-truth and migrate frontend API calls.
- [ ] Enforce loan/document access rules consistently across all endpoints.
- [ ] Add audit events for all state transitions: doc upload/review, acceptance, disbursement.

**Acceptance gate**
- [ ] Security regression tests: borrower cannot access other borrowers’ loans/documents; officer-only actions require officer role.

---

## 6) Immediate Next Actions (High-Leverage Order)

- [ ] Implement `/api/documents/*` endpoints first (unblocks UI2 doc panel parity).
- [ ] Implement `/api/loans/:id/accept-terms` (unblocks terms + signature + disbursement UX).
- [ ] Refactor borrower chat rendering to support workflow cards (unblocks the “UI2” feel).

---

## 7) Notes on Known Repo Cleanups (Non-Blocking)

- The current borrower design overlay path still points at the deleted directory in [App.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/frontend/src/App.tsx#L240-L246). It is dev-only and inert unless a querystring is set, but should be updated to the new source-of-truth location or removed once UI2 parity is reached.

