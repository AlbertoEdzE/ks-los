# Phase 2 Integration Notes (LOS v2)

## Objective

Phase 2 makes the borrower experience truly workflow-driven:

- Persisted conversation intelligence (intent summary, scores)
- Phase progression aligned to the phase tracker UI
- Recommended products derived from the catalog and borrower intent

---

## Components Integrated

1. **Borrower Chat**
   - Message send produces assistant response + structured metadata
   - Conversation fields updated after each message

2. **Phase Engine**
   - Active phases ordered by sort order
   - Borrower progression validates sequential transitions

3. **Recommendation Engine**
   - Reads catalog products
   - Produces structured recommended products payload

---

## API Contract Notes

- POST `/api/conversations/:id/messages` must:
  - create user message
  - create assistant message with metadata
  - update conversation fields atomically

