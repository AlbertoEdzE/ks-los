# Phase 2: Borrower Workflow Semantics

## Status: Planned

## Overview

Phase 2 makes borrower chat a persisted workflow:

- Conversation intelligence is stored (intent summary, seriousness/fit).
- Phases advance according to validated rules.
- Recommendations derive from the configured product catalog.

## Objectives

1. Structured metadata outputs on every borrower message.
2. Phase tracker reflects persisted `currentPhaseId` changes.
3. Product recommendations reflect catalog constraints and borrower intent.
4. E2E borrower flow is stable and reproducible.

## Architecture Notes

- Responses must include validated JSON metadata; do not rely on UI parsing.
- Updates to conversation state must be consistent with message metadata.

## Validation Criteria

- Refresh preserves conversation state and phase tracker state.
- Recommendations are catalog-driven (not hardcoded).
- Phase 2 test/validation/E2E reports exist.

