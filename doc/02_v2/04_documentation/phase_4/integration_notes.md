# Phase 4 Integration Notes (LOS v2)

## Objective

Phase 4 delivers the v2 “agentic wow” behaviors as workflow-native outputs:

- Approval probability navigator (likelihood + blockers + next actions)
- Autonomous completion baseline (checklists + reminders + mismatches)
- Explainable underwriting copilot (memo artifact with guardrails)

---

## Components Integrated

1. **Decisioning Outputs**
   - Approval likelihood score
   - Top blockers and top actions (with expected impact fields when available)
   - Counterfactual support for amount/tenure/product adjustments

2. **Completion Engine**
   - Required documents derived from catalog product
   - Document state tracking per loan
   - Exception detection (mismatch rules) and audit events

3. **Underwriting Copilot**
   - Underwriting memo schema and persistence
   - Guardrails enforcing compliance-safe language

