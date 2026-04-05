# Officer Hold Mapping — LNAI → LOS (Components, APIs, Models)

## 1) LNAI “shell” components relevant to officer hold
In the LNAI frontend, officer screens do not share the borrower “glass” shell. Instead, they use a lightweight officer shell:

| LNAI Component / Pattern | Location | Purpose | LOS Equivalent (recommended) |
|---|---|---|---|
| `OfficerChrome` | `frontend/src/App.tsx` | Top nav + logout; wraps all officer pages | `OfficerShellLayout` (new, additive) |
| `RequireAuth` / `RequireRole` | `frontend/src/App.tsx` | Route guards | Use existing LOS auth guard + RBAC checks |
| Two-column rail layout | Inline styles in officer pages | Left list + right detail | `SplitPaneLayout` or `MasterDetailLayout` component |
| “Saved” confirmation | local state in `DashboardPage` | immediate feedback after PATCH | LOS toast or inline “Saved” indicator (match LNAI visuals) |

---

## 2) LNAI Officer Hold UI mapping (Leads / approval blockers)

### 2.1 UI components (recommended decomposition)
| LNAI UI region (screen) | LNAI implementation | Data source | LOS component (proposed) |
|---|---|---|---|
| Officer Leads list | `/dashboard` `DashboardPage` left rail | `GET /api/conversations` | `OfficerHoldListPanel` |
| Lead selection state | local `selectedId` | N/A | `useSelectedHold()` hook |
| Lead detail form | right panel form fields | `Conversation` fields | `OfficerHoldDetailPanel` |
| Save action | `PATCH /api/conversations/{id}` | backend persistence | `useUpdateHoldMutation()` |
| Approval Probability card | “Approval Probability” section | `Conversation.approvalProbability` | `ApprovalNavigatorCard` |
| Blockers list | “Top blockers” | `approvalProbability.topBlockers[]` | `BlockersList` |
| Next actions list | “Next actions” | `approvalProbability.topActions[]` | `NextActionsList` |
| Recommended products | “Recommended Products” | `Conversation.recommendedProducts[]` | `RecommendedProductsCard` (optional) |

---

## 3) LNAI endpoints used by the officer hold UI (source of truth)

### 3.1 Leads (“holds”) endpoints
| Capability | LNAI endpoint | Method | Auth | Notes |
|---|---|---:|---|---|
| List leads | `/api/conversations` | GET | Officer-only | Used by `/dashboard` and `/officer-chat` |
| Update lead | `/api/conversations/{conversation_id}` | PATCH | Officer-only | Updates `status`, `borrowerName`, `assignedOfficer`, `currentPhaseId` |
| Get lead detail | `/api/conversations/{conversation_id}` | GET | Viewer role + restricted access | Used in officer chat refresh |
| List messages | `/api/conversations/{conversation_id}/messages` | GET | Viewer role + restricted access | Used by officer chat |

### 3.2 Loan/document “hold resolution” endpoints (pipeline)
| Capability | LNAI endpoint | Method | Auth | Notes |
|---|---|---:|---|---|
| List loans | `/api/loans` | GET | Officer-only | Pipeline source |
| Update loan | `/api/loans/{loan_id}` | PATCH | Officer-only | Set `currentPhaseId`, etc. |
| Patch checklist item status | `/api/loans/{loan_id}/documents` | PATCH | Officer-only | Update per-document status |
| Upload document | `/api/loans/{loan_id}/documents/upload` | POST | Officer-only | Multipart upload |
| Generate underwriting memo | `/api/loans/{loan_id}/underwriting-memo` | POST | Officer-only | Generates and stores memo JSON |
| STP process | `/api/loans/{loan_id}/stp-process` | POST | Viewer role + access checks | Sets `awaiting_documents` when docs missing |

---

## 4) Data model mapping (LNAI → LOS)

### 4.1 “Officer Hold” concept
LNAI does not have a dedicated `OfficerHold` table; “hold” is derived from:
- **Lead/Conversation**: approval blockers/actions + assignment + status
- **Loan**: `stp_processing_status` (e.g., `awaiting_documents`) + document checklist

Recommended LOS approach:
- Keep LOS canonical models (Lead/Application/Loan) intact.
- Create a **derived “OfficerHoldViewModel”** (DTO) for the UI, assembled server-side from existing LOS entities.

### 4.2 DTOs (recommended LOS contracts)

#### `OfficerHold`
Maps primarily to **LNAI Conversation**.
```ts
type OfficerHold = {
  id: string;
  borrowerName: string | null;
  status: "active" | "reviewing" | "qualified" | "closed" | string;
  assignedOfficer: string | null;
  approvalProbability: ApprovalProbabilityNavigator | null;
  recommendedProducts?: Array<{ name: string; recommendation?: string }>;
  createdAt?: string;
};
```

#### `ApprovalProbabilityNavigator`
Matches LNAI backend schema in `v2_conversations_router.py`.
```ts
type ApprovalProbabilityNavigator = {
  probability: number; // 0..1
  band: "low" | "medium" | "high";
  topBlockers: Array<{ title: string; severity: "low" | "medium" | "high"; detail: string }>;
  topActions: Array<{ title: string; impact: "low" | "medium" | "high"; detail: string }>;
  inputsUsed: {
    creditScore?: number | null;
    monthlyIncome?: number | null;
    existingDebts?: number | null;
    loanAmount?: number | null;
    dti?: number | null;
    loanToIncome?: number | null;
  };
  method: string;
  asOf: string; // ISO timestamp
};
```

#### `LoanHold` (optional, if LOS mirrors pipeline hold resolution)
Maps to **LNAI Loan** when `stp_processing_status` indicates a hold.
```ts
type LoanHold = {
  id: string;
  borrowerName: string | null;
  status: string;
  currentPhaseId: string | null;
  stpProcessingStatus: "awaiting_documents" | "processing" | "awaiting_acceptance" | "completed" | string | null;
  documentChecklist?: {
    items: Array<{ name: string; status: "missing" | "submitted" | "verified" | "rejected"; updatedAt: string }>;
  };
};
```

---

## 5) Service integration mapping (what LOS must implement)

### 5.1 Auth and RBAC
LNAI uses a dev token (`Bearer loan-officer-access`) to gate officer endpoints.
In LOS production:
- Use LOS SSO/JWT session
- Enforce officer role/permissions on:
  - list holds/leads
  - update holds
  - access loan/document hold resolution actions

### 5.2 Auditing and observability
LNAI logs audit events for updates.
LOS should:
- Emit an audit event for each hold update
- Include correlation IDs on requests
- Track metrics for:
  - list holds
  - update hold fields
  - document upload/review actions (if enabled)

---

## 6) “Without modifying existing code” implementation strategy (LOS)
To keep changes additive and avoid touching existing LOS features:
1. Add a new route (e.g., `/officer/holds`) via LOS’s extension mechanism.
2. Implement new backend endpoints that read existing LOS data and output the LNAI-shaped DTOs.
3. Implement new frontend module that consumes only the new endpoints.
4. Gate rollout behind a feature flag.

