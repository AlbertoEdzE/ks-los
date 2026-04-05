# LOS Officer Hold — Implementation Plan (Pixel-Perfect LNAI Replica)

## 0) Scope and constraints
- **Goal:** Build a **functional officer hold view** in the LOS system that visually and behaviorally mirrors the LNAI officer hold UI, including workflows, interactions, and data handling.
- **Constraint:** Implement as an **additive feature** (no refactors required). Do not modify the LNAI repo; treat it as the reference implementation/design system.
- **Assumption:** LOS is a separate system/codebase. This plan specifies integration points and artifacts LOS must implement; exact file paths will differ.

---

## 1) Definition of Done (DoD) for “pixel-perfect”
To be considered a true LNAI replica, LOS must match:
1. **Layout**: grid structure, rails, gutters, alignment, scroll regions
2. **Visual tokens**: colors, radii, shadows, borders, translucency rules
3. **Typography**: font family (Inter), sizes, weights, letter spacing
4. **Interactive states**: hover/active/selected/disabled/focus, toasts, loading/error states
5. **Workflows**:
   - Lead list → select → edit fields → save → reflect server state
   - “Hold” content rendering (blockers/actions) from server data
   - If included: loan-level hold resolution (documents, STP)
6. **Accessibility**: keyboard navigation, visible focus, ARIA labeling, color contrast, semantic structure
7. **Test coverage**: unit + integration + E2E + visual regression

---

## 2) Reference LNAI behavior to replicate

### 2.1 Officer Leads “Hold” (approval blockers/actions)
Reference screen:
- **Route (LNAI):** `/dashboard`
- **Hold UI:** “Approval Probability” section displaying:
  - Percent score
  - Top blockers (title + detail)
  - Next actions (title + detail)
Actions:
- Select lead in left rail
- Edit: borrower name, assigned officer, status
- Save (PATCH) and show “Saved” state

### 2.2 Officer Loans “Hold” (documents/STP)
Reference screen:
- **Route (LNAI):** `/pipeline`
Hold semantics:
- `stp_processing_status = awaiting_documents` indicates a “hold” requiring more documents.
Officer actions:
- Update document checklist statuses
- Upload documents
- Generate underwriting memo
- Move loan phase

---

## 3) Implementation approach (recommended)

### 3.1 Create a dedicated, isolated Officer Hold module in LOS
Add a new feature module (names illustrative):
- `OfficerHoldPage` (route container)
- `OfficerHoldLayout` (shell composition)
- `OfficerHoldListPanel` (left rail: leads/holds list)
- `OfficerHoldDetailPanel` (right panel)
- `ApprovalNavigatorCard` (probability + blockers + actions)
- `RecommendedProductsCard` (optional, if mirrored)
- `HoldResolutionPanel` (optional: document checklist + actions)

**Key:** do not reuse or modify existing LOS pages; integrate via LOS’s standard routing/plugin mechanism.

### 3.2 Recreate the LNAI design tokens in LOS (do NOT “approximate”)
Extract and codify the tokens used by LNAI officer pages:
- Colors (examples observed):
  - Primary: `#0078D4` (borrower surfaces)
  - Officer neutrals: borders `#e5e7eb`, selection `#eff6ff`, text `#111827`, muted `#6b7280`
  - Titles: `#1B2A4A` (borrower theme)
- Radii:
  - borrower: `rounded-2xl/3xl`
  - officer pages: `borderRadius: 10–12px` (inline styles)
- Spacing:
  - left rail widths: ~`320px` (leads), ~`360px` (pipeline)

**Implementation options (pick one, but keep it consistent):**
1. **Tailwind (preferred if LOS already uses Tailwind):** create `lnai-*` token classes via config + CSS variables.
2. **CSS variables + CSS Modules:** define `--lnai-*` variables and use them in component-scoped styles.
3. **Design system wrapper:** implement `LNAIButton`, `LNAICard`, etc. and compose the page.

---

## 4) Backend integration plan (LOS)

### 4.1 Data needed for Officer Leads hold view
From LNAI, the UI expects a “conversation/lead” object with:
- `id`
- `borrowerName`
- `status`
- `assignedOfficer`
- `approvalProbability` (navigator object):
  - `probability` (0..1)
  - `band` (`low|medium|high`)
  - `topBlockers[]` (≤3): `{title, severity, detail}`
  - `topActions[]` (≤3): `{title, impact, detail}`
  - `inputsUsed`, `method`, `asOf`
- `recommendedProducts[]` (optional in hold screen)

### 4.2 LOS service contracts (proposed)
If LOS does not already have equivalents, implement endpoints that mirror LNAI semantics:
- `GET /los/api/officer/holds`  
  Returns list of officer-hold items (lead-centric) with the fields above.
- `GET /los/api/officer/holds/{id}`  
  Returns detail (if list payload is intentionally small).
- `PATCH /los/api/officer/holds/{id}`  
  Allows updating:
  - assigned officer
  - lead status
  - borrower name (if LOS permits)

**Auth/RBAC**
- Require “Loan Officer” role.
- Enforce tenant/org scoping if applicable.
- Add audit events for every update.

### 4.3 Loan “awaiting_documents” holds (optional extension)
If LOS wants to mirror the pipeline hold resolution UI, also expose:
- `GET /los/api/officer/loans?holdStatus=awaiting_documents`
- `PATCH /los/api/officer/loans/{id}/documents` (update checklist statuses)
- `POST /los/api/officer/loans/{id}/documents/upload`
- `POST /los/api/officer/loans/{id}/underwriting-memo`

---

## 5) State management & data flow (frontend in LOS)

### 5.1 Recommended frontend patterns
Use a request layer + caching:
- `React Query` (or LOS’s standard equivalent) for:
  - leads list query
  - lead detail query
  - update mutations (optimistic updates optional)

Local UI state:
- `selectedHoldId`
- `draftBorrowerName`, `draftAssignedOfficer`, `draftStatus`
- `saveBusy`, `saveOk`, `saveError`

### 5.2 Error/loading parity with LNAI
Replicate:
- “Loading…” placeholders in list/detail areas
- inline error messaging (red text)
- saved confirmation state (“Saved”)

---

## 6) Responsive design strategy
LNAI officer pages are effectively “desktop-first”. For production LOS:
- **Desktop (≥1024px):** 2-column grid (left rail + detail).
- **Tablet (768–1023px):** collapsible left rail or top tabs.
- **Mobile (<768px):** single-column, list-first then detail drill-in.

Do not change the desktop visuals; only adapt at breakpoints.

---

## 7) Accessibility compliance checklist
Minimum requirements:
- All interactive elements keyboard-focusable
- Visible focus ring (do not remove outlines)
- Labels:
  - inputs: `label` + `htmlFor`
  - list items: accessible name includes borrower name + status
- Buttons have clear names (“Save”, “Upload”, etc.)
- Ensure color contrast for muted text on light backgrounds
- If dialogs/modals are used, use a11y-safe primitives (Radix, Headless UI, etc.)

---

## 8) Testing plan (must include visual regression)

### 8.1 Unit tests
- Component rendering:
  - `ApprovalNavigatorCard` (empty vs populated)
  - list selection states
  - form validation behavior (if any)

### 8.2 Integration tests
- Data mapping correctness from API → UI view model
- Mutation behavior: save updates + error handling + refresh behavior

### 8.3 E2E tests (workflow parity)
- Login as officer → open officer hold view
- Load holds list → select a hold
- Edit assigned officer → save → verify persistence after refresh
- Verify blockers/actions visible when present

### 8.4 Visual regression (pixel-perfect gate)
Adopt a Playwright screenshot diff approach similar to LNAI’s `ui_design_parity.spec.ts`:
- Store baseline PNGs from approved design exports
- On CI:
  - render page at fixed viewport sizes
  - screenshot
  - compare with `pixelmatch` (threshold tuned)
  - fail build if diff ratio exceeds allowed tolerance

---

## 9) Phased delivery plan

### Phase 1 — Foundations (1–2 sprints)
- Lock design baselines (PNG exports per viewport)
- Implement LOS design token layer (`lnai-*`)
- Implement Officer Hold route + shell layout
- Implement list + detail selection behavior (static mock data)

### Phase 2 — Functional data integration (1 sprint)
- Implement LOS endpoints or service adapters
- Wire queries/mutations
- Add caching + optimistic updates (optional)
- Add audit logging on updates

### Phase 3 — “Hold resolution” expansion (optional)
- Add loan/document hold resolution panel mirroring LNAI pipeline
- Add document upload + checklist updates

### Phase 4 — Quality gates (continuous)
- Add full unit/integration suite
- Add E2E workflows
- Add visual regression gates
- Accessibility audit (axe + manual keyboard testing)

