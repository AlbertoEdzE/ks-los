# Officer Hold — Visual Parity (Pixelmatch) in LOS

This repo already includes a Playwright + pixelmatch harness at:
- `e2e/tests/ui_design_parity.spec.ts`

It compares runtime screenshots against design PNGs stored in:
- `doc/02_Loan-Navigator-AI/attached_assets/*.png`

## What was added
The new route is now included in the parity matrix:
- `/officer-hold`

## How to run (local)
1. Ensure the API + frontend are running (same as existing e2e guidance).
2. Place your approved baseline PNG exports in:
   - `doc/02_Loan-Navigator-AI/attached_assets/`
3. Run:
```bash
UI_PARITY=1 npm run test:e2e -- officer_hold
```
or run the full parity job:
```bash
UI_PARITY=1 npm run test:e2e -- ui_design_parity
```

## Output artifacts
Diff outputs are written to:
- `e2e/test-results/ui-design-parity/`

You will get:
- `*.baseline.png` (copied baseline)
- `*.actual.png` (runtime screenshot)
- `*.diff.png` (pixel diffs)
- `best-matches.json` and `all-scores.json`

