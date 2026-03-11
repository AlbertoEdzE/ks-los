# Phase 4 Validation Report (LOS v2)

## Validation Objective

Validate that the v2 “wow features” exist as workflow outputs and are stable, testable, and auditable.

---

## Approval Probability Navigator Validation

- [ ] Approval likelihood is computed and persisted on the conversation/loan
- [ ] Top blockers are present and consistent with configured constraints
- [ ] Next actions are present and actionable
- [ ] Counterfactual changes update outputs predictably

---

## Autonomous Completion Validation

- [ ] Required document checklist exists per loan/product
- [ ] Missing documents are detectable and surfaced
- [ ] Reminders/escalations emit audit events and are idempotent
- [ ] Mismatch detection rules trigger exceptions (when applicable)

---

## Underwriting Copilot Validation

- [ ] Underwriting memo is generated with required sections
- [ ] Memo includes evidence references (catalog/policy/model factors when available)
- [ ] Guardrails prevent promises and non-compliant language

---

## Exit Criteria

Phase 4 is accepted when:

- Unit + integration tests pass for probability, checklist, and memo artifacts
- Playwright E2E scenarios confirm surfaces appear and persist
- Audit evidence exists for all state mutations and automated actions

