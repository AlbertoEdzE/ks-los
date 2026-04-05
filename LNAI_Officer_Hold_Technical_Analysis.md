# LNAI Officer Hold — Technical Analysis (Local Repo)

## 1) What “Officer Hold” means in this codebase
In this repository, “officer hold” is not implemented as a single dedicated module named `OfficerHold`. Instead, the officer-facing “hold” experience is composed from two related concepts that show up in the UI and data model:

1. **Lead-level “holds” / blockers** via the **Approval Probability Navigator** (a computed object stored on `Conversation.approval_probability`), rendered in:
   - **Route:** `/dashboard` (Officer “Leads” page)
   - **UI blocks:** “Approval Probability”, “Top blockers”, “Next actions”

2. **Loan-level “holds” due to missing documents** via **STP processing** (loan field `Loan.stp_processing_status` can be `awaiting_documents`), surfaced primarily in:
   - **Route:** `/pipeline` (Officer “Loans” page)
   - **UI blocks:** document checklist + document review/update flows (and related STP processing status)

If your target LNAI “officer hold view” is a specific Figma screen, confirm whether it corresponds to **Leads (approval blockers)**, **Loans (document/STP holds)**, or a combined view. This analysis covers both because both drive “hold” states in practice.

---

## 2) Repository structure (relevant to officer hold)

### Frontend (React + Vite + Tailwind v4)
**Folder:** `frontend/`

Key entry points:
- `frontend/src/main.tsx`: React app bootstrap; wraps app with:
  - `BrowserRouter` (react-router-dom)
  - `QueryClientProvider` (TanStack React Query)
  - `ThemeProvider` (adds/removes `html.dark`)
  - `Toaster` (sonner)
- `frontend/src/App.tsx`: **monolithic route and page implementation** (borrower + officer).

UI components used across the app:
- `frontend/src/components/ChatInterface.tsx`: borrower experience and some shared data parsing
- `frontend/src/components/DocumentsCard.tsx`: borrower document checklist card UI
- `frontend/src/components/*`: metrics, simulator, admin tools, etc.

Testing:
- Unit/integration: `vitest` + Testing Library (e.g., `frontend/src/App.test.tsx`)
- E2E: `playwright` under `e2e/`

### Backend (FastAPI + SQLAlchemy)
**Folder:** `src/`

Entry points:
- `src/main.py`: FastAPI app; mounts routers for v2/v3 APIs, metrics, etc.

Officer hold related routers:
- `src/api/routers/v2_conversations_router.py`
  - `GET /api/conversations` (officer-only) → lead list for dashboard
  - `PATCH /api/conversations/{id}` (officer-only) → update lead fields
  - approval probability navigator schema and computation
- `src/api/routers/v2_loans_router.py` + `src/api/routers/v2_documents_router.py` + `src/api/routers/v2_loan_acceptance_router.py`
  - loan pipeline + documents + STP statuses (including `awaiting_documents`)
- `src/api/routers/v2_phases_router.py`
  - loan phase model and knowledge (includes references to “compliance holds” as part of domain knowledge)

Data models:
- `src/shared/db.py`
  - `Conversation.approval_probability` (JSON)
  - `Conversation.assigned_officer`
  - `Loan.stp_processing_status` (Text; `awaiting_documents`, `awaiting_acceptance`, etc.)
  - `Loan.document_checklist` (JSON)

---

## 3) Officer-facing screens and where “hold” shows up

### A) Officer Leads (Dashboard) — `/dashboard`
**Implementation:** `frontend/src/App.tsx` → `DashboardPage` + `OfficerChrome`

Core workflow:
1. Officer logs in → role becomes `admin` in the frontend (dev login mode).
2. Navigate to **Dashboard**.
3. UI fetches leads via `GET http://localhost:8000/api/conversations` with header:
   - `Authorization: Bearer loan-officer-access`
4. Officer selects a lead in a left-hand list.
5. Right side shows lead detail and allows updates:
   - Borrower name
   - Assigned officer
   - Status (active/reviewing/qualified/closed)
6. Officer clicks **Save** → `PATCH /api/conversations/{id}`.
7. **Hold/Blocker** information is displayed under “Approval Probability”:
   - Percentage score
   - “Top blockers” (from `approvalProbability.topBlockers`)
   - “Next actions” (from `approvalProbability.topActions`)

UI composition (page-level):
- `OfficerChrome`: simple top bar with links (Dashboard, Pipeline, Loan Products, Officer Chat, …).
- Two-column layout:
  - Left: leads list (scroll container)
  - Right: lead detail form + “Approval Probability” and “Recommended Products” sections

“Hold” data dependencies:
- `Conversation.approval_probability` JSON is rendered as:
  - `probability`: float 0..1
  - `topBlockers`: up to 3 items `{title, severity, detail}`
  - `topActions`: up to 3 items `{title, impact, detail}`
- The dashboard **does not compute** hold data locally; it only renders what the backend has stored on each `Conversation`.

### B) Officer Loans (Pipeline) — `/pipeline`
**Implementation:** `frontend/src/App.tsx` → `PipelinePage` + `OfficerChrome`

Core workflow:
1. Fetch phases → `GET /api/phases` (no officer header required by the frontend call in this repo).
2. Fetch loans → `GET /api/loans` (officer-only in backend; frontend passes officer bearer token).
3. Officer selects a loan, then:
   - views/updates document checklist items (`PATCH /api/loans/{id}/documents`)
   - uploads documents (`POST /api/loans/{id}/documents/upload`)
   - generates underwriting memo (`POST /api/loans/{id}/underwriting-memo`)
   - updates loan phase (`PATCH /api/loans/{id}`)

“Hold” data dependencies:
- If STP processing is triggered and documents are insufficient, backend sets:
  - `Loan.stp_processing_status = "awaiting_documents"`
  - (see `_run_stp()` in `v2_loan_acceptance_router.py`)
- This creates a real “hold” state that requires officer/borrower action (document upload) to proceed.

---

## 4) Styling patterns and design-system signals

### Borrower UI: Tailwind-first, “glass” variants, strong tokens
The borrower-facing UI (and some shared cards) use Tailwind utility classes heavily, with:
- **Primary brand color:** `#0078D4` (and `#005EA6` as darker gradient)
- **Title/text color:** `#1B2A4A`
- **High-radius surfaces:** `rounded-2xl`, `rounded-3xl`
- **Translucent surfaces:** `bg-white/80`, `dark:bg-white/[0.04]`, `backdrop-blur-*`
- **Custom “glass” theme hooks** in `frontend/src/index.css` using `.glass-*` classes
- **Dark mode** via `html.dark` and `@custom-variant dark`

Pixel-perfect support hints:
- `BorrowerHomePage` includes a *dev-only* “design overlay png” + opacity slider, suggesting a workflow for overlaying Figma exports while tuning UI.

### Officer UI: inconsistent styling (inline style blocks)
Officer pages (`DashboardPage`, `PipelinePage`, `LoanProductsPage`, etc.) are primarily implemented with **inline styles** inside `App.tsx`:
- Borders: `#e5e7eb`, backgrounds `#fff`, `#fafafa`, selection `#eff6ff`
- Grid columns hard-coded (`320px/360px` left rail + `1fr` detail panel)
- Less reuse of Tailwind tokens compared to borrower UI

Implication for replication:
- If you need an **exact pixel-perfect officer hold replica**, you must decide whether to:
  1) replicate the inline-style approach exactly, or
  2) refactor into reusable components/tokens (recommended for maintainability, but it is not how this repo currently does it for officer screens).

---

## 5) Data flow and state management (officer hold relevant)

Frontend state:
- No global store (no Redux/Zustand). Pages use `useState`, `useMemo`, `useEffect`.
- React Query is present and used in other parts of the app, but officer pages in `App.tsx` mostly use raw `fetch`.

Backend storage:
- `Conversation` stores the approval navigator JSON blob and officer assignment.
- `Loan` stores STP status and the document checklist JSON blob.

Auth/RBAC:
- Frontend uses a dev “role” (`user` vs `admin`) gate in `RequireRole`.
- Backend gates officer endpoints via bearer token check:
  - `Authorization: Bearer loan-officer-access` (default dev token)
  - see `src/shared/auth.py` (DEV_OFFICER_TOKEN)

---

## 6) Technical complexity assessment for pixel-perfect replication

### Complexity level: **High** (for an exact replica across systems)
Even though the officer “hold” UI is not deeply componentized, achieving **pixel-perfect** replication in a different LOS codebase is high-complexity because:

1. **Two styling paradigms coexist**
   - Borrower UI: Tailwind tokens + translucent surfaces + dark/glass variants
   - Officer UI: inline styles (different spacing, radii, border palette)
   A replica must match whichever paradigm your target LNAI design actually uses.

2. **Design tokens are not centralized**
   Colors and spacing are repeated as literals (hex + Tailwind arbitrary values). A replica must re-create these tokens (and keep them consistent) to avoid drift.

3. **Backend-derived “hold” states**
   - Approval blockers/actions are *computed and stored* server-side.
   - STP “awaiting_documents” is driven by document availability.
   If LOS data models differ, mapping and reconciliation are non-trivial.

4. **Test expectations imply visual regression**
   The repository already contains Playwright + pixelmatch infrastructure for screenshot diffs. A true pixel-perfect effort should include similar testing in LOS.

### Primary risk areas
- Typography mismatch (Inter vs system fonts; font rendering differences)
- CSS stacking and translucency differences (backdrop blur, alpha)
- Responsive behavior (LNAI officer pages are not strongly responsive; LOS may require responsiveness)
- Data shape mismatches (approval probability sometimes treated as number vs object in TS types)

