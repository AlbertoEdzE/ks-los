# Phase 2 Test Report (LOS v2)

## Scope

Phase 2 testing validates:

- Intent summary extraction and persistence
- Seriousness/fit scoring and persistence
- Phase progression logic for borrower conversations
- Recommended products payload generation and persistence

---

## Unit Tests

- [ ] Intent summary schema validation
- [ ] Scoring logic determinism tests
- [ ] Phase transition rules (sequential progression)
- [ ] Recommendation selection rules (catalog constraints)

---

## Integration Tests

- [ ] Sending borrower message updates conversation fields correctly
- [ ] Message metadata includes intent summary and recommendations (when applicable)
- [ ] Phase update only advances when allowed

---

## E2E (Playwright)

- [ ] Borrower welcome → start chat → send message → see phase tracker
- [ ] Refresh preserves conversation and phase state

