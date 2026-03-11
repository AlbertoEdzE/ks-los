# User Guide (LOS v2)

## Borrower Experience

### Borrower Chat

The borrower starts at the chat interface and is guided through phases while receiving recommendations.

Key expected behaviors:

- A new chat creates a conversation.
- Sending messages persists the interaction history.
- A phase tracker shows progress through the loan journey.
- The assistant generates structured recommendations aligned to available products.

UI reference: [chat.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/chat.tsx)

---

## Officer Experience

### Officer Dashboard

The officer dashboard lists leads (conversations) and surfaces AI-extracted insights.

Key expected behaviors:

- Leads appear as borrowers create conversations.
- Seriousness and fit scores appear when available.
- Selecting a lead shows detail and history.
- Officers can assign or update statuses (where enabled).

UI reference: [officer-dashboard.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/officer-dashboard.tsx)

### Loan Pipeline

The loan pipeline organizes loans by phase. Officers can select a loan and update its details.

UI reference: [loan-pipeline.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/loan-pipeline.tsx)

### Loan Product Catalog

Officers configure lending products. The catalog powers recommendations and eligibility logic.

UI reference: [loan-products.tsx](file:///Users/albertohernandez/Documents/projects/ks-los/doc/02_Loan-Navigator-AI/client/src/pages/loan-products.tsx)

---

## System Behaviors Users Should Rely On

- The system never promises approvals; it guides and explains constraints.
- Every operational state change (loan updates, phase changes, product changes) is auditable.
- Recommendations are grounded in configured products and captured borrower intent.

