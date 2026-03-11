# Phase 1: UI Wiring + Product API Skeleton

## Status: Planned

## Overview

Phase 1 establishes a design-exact frontend aligned to `/doc/02_Loan-Navigator-AI/client` and a contract-complete backend skeleton that makes all UI pages functional (even if intelligence is initially stubbed).

## Objectives

1. UI parity for borrower and officer routes.
2. Product API endpoints exist and match UI expectations.
3. Persistence exists for workflow-first domain entities and supports deterministic seeding.
4. Scientific rigor: unit + integration + Playwright E2E smoke with reports.

## Architecture Notes

- UI is the contract; backend must adapt to it.
- Entities required: conversations, messages, phases, loans, catalog products.
- Officer boundary enforced (POC token acceptable in Phase 1).

## Implementation Steps

1. Stand up frontend routes and pages mirroring the reference UI.
2. Implement the product API endpoints required by the UI.
3. Implement persistence schema and idempotent seeds for phases/products.
4. Add tests and publish Phase 1 reports under `/doc/02_v2/04_documentation/phase_1/`.

## Validation Criteria

- All routes render with correct empty/seeded states.
- All UI-called endpoints exist and return valid envelopes.
- E2E smoke passes.

