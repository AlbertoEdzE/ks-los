# Global Credit Policy v1.0

## 1. Credit Score Bands & Actions
- **Super Prime (720+)**: Auto-Approval eligible if DTI < 40%.
- **Prime (660-719)**: Approval eligible.
- **Near Prime (620-659)**: Manual Review required. Max DTI 35%.
- **Subprime (<620)**: Decline, unless "Recovering" segment with strong recent payment history.

## 2. Thin File Policy
- **Definition**: < 2 trade lines or < 2 years history.
- **Action**: 
    - If Age < 25 ("Young"): Refer to "Emerging Credit" program. Cap limit at $2,000 XCD.
    - If Age >= 25: Manual Review required. Proof of income mandatory.

## 3. Debt-to-Income (DTI) Ratios
- **Maximum Backend DTI**: 43% for standard approval.
- **Exceptions**: Up to 50% for Super Prime with > 12 months reserves.

## 4. Territory Specifics
- **Antigua and Barbuda (AG)**: Standard policy applies.
- **Grenada (GD)**: Minimum score for auto-approval is 740 due to higher local default rates.
- **Saint Lucia (LC)**: Proof of address requires 2 utility bills.

## 5. Derogatory Marks
- **Bankruptcy**: Automatic Decline if discharged < 2 years ago.
- **Foreclosure**: Automatic Decline if < 3 years ago.
- **Collections**: Must be paid in full if > $500 XCD.

## 6. Synthetic/Test Accounts
- Accounts flagged as "synthetic_archetype" must be processed but flagged for "Simulation Mode".
