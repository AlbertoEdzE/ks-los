# KS-LOS Borrower Journey: Conversation Flow Analysis & Fix

**Date:** March 26, 2026  
**Issue:** JSON/XML tags leaking into UI, metadata not populating correctly  
**Root Cause:** LLM response parsing not implemented in v3 router

---

## 🔍 Problem Analysis

### Observed Issues (from screenshot)

1. **Inline JSON displayed to user:**
   ```
   ... so we can find the most affordable option. { "purpose": "home_purchase" }
   ```

2. **Repeated JSON in subsequent messages:**
   ```
   ... before deductions? { "purpose": "home_purchase" }
   ```

3. **Network error appearing** (likely timeout from LLM processing)

4. **Metadata not populating UI cards** (loan snapshot, recommendations not showing)

### Root Cause

The v3 router was returning the **raw LLM response** directly to the frontend without:
1. Stripping XML tags and inline JSON from the display text
2. Parsing XML tags to populate the metadata object

The LLM is correctly generating responses with XML-tagged structured data, but this data needs to be:
- **Extracted** → Parsed from XML into JSON for metadata
- **Stripped** → Removed from display text for clean conversation

---

## 📚 Borrower Journey Logic: The 7-Step Flow

The KS-LOS system uses a **3-mode, 7-step** borrower journey:

### Mode 1: Advisory (Understanding & Estimation)

**Step 1: Intent Capture**
- **Goal:** Understand loan purpose and borrower name
- **Extracts:** `purpose`, `borrower_name`, `urgency`
- **LLM Question:** "What are you looking to achieve? Home, car, business, or personal loan?"
- **UI Components:** None (pure conversation)
- **Transition:** When `purpose` confidence > 0.7

**Step 2: Financial Context**
- **Goal:** Capture employment and income
- **Extracts:** `employment_type`, `monthly_income`, `business_details`
- **LLM Question:** "Are you salaried, self-employed, or contractor? What's your monthly income?"
- **UI Components:** None (pure conversation)
- **Transition:** When `employment_type` AND `monthly_income` confidence > 0.7

**Step 3: Loan Details**
- **Goal:** Capture loan amount, tenure, existing debts
- **Extracts:** `loan_amount`, `loan_tenure_years`, `existing_debts`, `credit_history`
- **LLM Question:** "How much are you looking to borrow? Any existing loans or credit card balances?"
- **UI Components:** None (pure conversation)
- **Transition:** When `loan_amount` AND `existing_debts` captured

**Step 3b: Contact Information** (parallel to Step 3)
- **Goal:** Capture contact details
- **Extracts:** `email`, `phone`, `property_location`
- **LLM Question:** "What's your email and phone number?"
- **UI Components:** None (pure conversation)
- **Transition:** When `email` AND `phone` captured

**Step 4: Snapshot & Recommendations**
- **Goal:** Generate loan recommendations
- **Computes:** EMI, affordability, credit risk
- **Generates:** 3 loan product recommendations
- **UI Components:**
  - `LoanSnapshotCard` - Shows loan metrics
  - `LoanCard` × 3 - Shows recommended products
- **Transition:** When user selects a recommendation

### Mode 2: Application (Collection & Submission)

**Step 5: Document Collection**
- **Goal:** Collect required documents
- **Generates:** `documents_checklist` based on loan type
- **UI Components:**
  - `DocumentsCard` - Shows required documents
  - Document upload with OCR
- **Transition:** When all required documents uploaded

**Step 6: Application Submission**
- **Goal:** Submit loan application
- **Triggers:** STP (Straight-Through Processing)
- **UI Components:**
  - `StpProcessingCard` - Shows STP progress
  - `AffordabilityCard` - Shows affordability analysis
- **Transition:** When STP completes

### Mode 3: Completion (STP, Acceptance, Disbursement)

**Step 7: Offer & Acceptance**
- **Goal:** Present loan offer and get acceptance
- **Generates:** `terms_acceptance` document
- **UI Components:**
  - `TermsAcceptanceCard` - Shows terms for signature
  - E-signature capture
- **Transition:** When terms accepted

**Final: Disbursement**
- **Goal:** Complete loan disbursement
- **Updates:** `disbursement` details
- **UI Components:** Confirmation message
- **Transition:** Journey complete

---

## 🧠 LLM Integration: How It Works

### LLM Response Format

The LLM generates responses with **XML-tagged JSON** for structured data:

```
That's wonderful! A home purchase is a major milestone. To help me structure the 
best path for you, could you share more details? Specifically, I'd love to know 
what the property value or loan amount is, and what you're planning for a down 
payment so we can find the most affordable option.

<intent_analysis>
{
  "purpose": "home_purchase",
  "urgency": "high",
  "seriousness_score": 85
}
</intent_analysis>
```

### Required Parsing

The v3 router must:

1. **Parse XML tags** → Extract JSON for metadata
2. **Strip XML tags** → Clean text for display
3. **Strip inline JSON** → Remove any `{...}` objects

### Correct Flow

```
LLM Response (raw)
    ↓
parse_llm_response()
    ↓
┌─────────────────────────────┬─────────────────────────────┐
│   clean_response_text       │   parsed_metadata           │
│   (for display)             │   (for UI cards)            │
├─────────────────────────────┼─────────────────────────────┤
│ "That's wonderful! A home   │ {                           │
│ purchase is a major         │   "intentAnalysis": {       │
│ milestone. To help me       │     "intentSummary": {      │
│ structure the best path     │       "purpose":            │
│ for you..."                 │       "home_purchase"       │
│                             │     }                       │
│                             │   }                         │
│                             │ }                           │
└─────────────────────────────┴─────────────────────────────┘
```

---

## ✅ Implementation: The Fix

### File: `src/shared/xml_parser.py` (NEW)

```python
def parse_llm_response(content: str) -> Tuple[str, Dict[str, Any]]:
    """
    Parse LLM response with XML-tagged structured data.
    
    Returns:
        - clean_text: Text with XML/JSON removed for display
        - metadata_dict: Parsed JSON from all XML tags
    """
    metadata = {}
    
    # Extract each XML tag
    for tag_name in ["intent_analysis", "loan_snapshot", ...]:
        json_str = extract_xml_tag(content, tag_name)
        if json_str:
            parsed = parse_json_safely(json_str, tag_name)
            if parsed:
                metadata[camel_case(tag_name)] = parsed
    
    # Strip XML tags and inline JSON from content
    clean_text = strip_xml_tags(content)
    
    return clean_text, metadata
```

### File: `src/api/routers/v3_agentic_conversations_router.py` (UPDATED)

```python
@router.post("/{session_id}/messages")
async def send_message(session_id: str, request: V3MessageRequest):
    # ... process through nodes ...
    
    # NEW: Parse XML from LLM response
    raw_response_text = state.conversation_history[-1].content
    clean_response_text, parsed_metadata = parse_llm_response(raw_response_text)
    
    # Create message with clean content and parsed metadata
    assistant_message = {
        "content": clean_response_text,  # Clean for display
        "metadata": parsed_metadata,     # Parsed for UI cards
        ...
    }
    
    return V3MessageResponse(
        response=clean_response_text,
        message=assistant_message,
        ...
    )
```

---

## 🧪 Testing

### Test Case 1: Intent Capture

**Input:**
```
User: "I want a home loan to buy a house."
```

**Expected LLM Response:**
```
That's wonderful! A home purchase is a major milestone. To help me structure 
the best path for you, could you share more details? Specifically, I'd love 
to know what the property value or loan amount is, and what you're planning 
for a down payment so we can find the most affordable option.

<intent_analysis>
{"purpose": "home_purchase", "urgency": "medium"}
</intent_analysis>
```

**Expected Output:**
- **Display:** "That's wonderful! A home purchase is a major milestone..."
- **Metadata:** `{"intentAnalysis": {"intentSummary": {"purpose": "home_purchase"}}}`
- **UI:** No cards (yet)

### Test Case 2: Recommendations

**Input:** (After all financial details captured)

**Expected LLM Response:**
```
Excellent! Based on your financial profile, I've analyzed the best options 
for you. Here are my top 3 recommendations...

<loan_snapshot>
{"loan_amount": 350000, "monthly_emi": 2850, ...}
</loan_snapshot>

<loan_recommendations>
[{"name": "Home Loan Plus", "interest_rate": 8.4, ...}, ...]
</loan_recommendations>
```

**Expected Output:**
- **Display:** "Excellent! Based on your financial profile..."
- **Metadata:** `{"loanSnapshot": {...}, "loanRecommendations": [...]}`
- **UI:** LoanSnapshotCard + 3× LoanCard

---

## 📊 State Machine: Advisory Mode Steps

```python
def _determine_step(state):
    # Step 4: Have ALL required fields
    if (context.purpose and context.loan_amount and
        context.monthly_income and context.employment_type and
        context.email and context.phone):
        return "snapshot_and_recommendations"
    
    # Step 3b: Have financials, need contact info
    if (context.purpose and context.loan_amount and
        context.monthly_income and context.employment_type):
        return "contact_capture"
    
    # Step 3: Have employment/income, need loan amount
    if context.employment_type and context.monthly_income:
        return "financial_details"
    
    # Step 2: Have purpose, need employment/income
    if context.purpose:
        return "employment_income"
    
    # Step 1: Need to understand purpose
    return "understand_need"
```

---

## 🎯 UI Components & Their Metadata Requirements

| Component | Required Metadata | Trigger |
|-----------|------------------|---------|
| `LoanSnapshotCard` | `metadata.loanSnapshot` | Step 4 |
| `LoanCard` × 3 | `metadata.loanRecommendations` | Step 4 |
| `DocumentsCard` | `metadata.documentsChecklist` | Step 5 |
| `StpProcessingCard` | `metadata.stpProcessing` | Step 6 |
| `AffordabilityCard` | `metadata.affordability` | Step 6 |
| `TermsAcceptanceCard` | `metadata.termsAcceptance` | Step 7 |

---

## 🔧 Network Error: Secondary Issue

The "Network error" in the screenshot is likely caused by:
1. **LLM timeout** - Ollama taking >30s to respond
2. **No retry logic** - Frontend gives up after one failed attempt

### Fix: Frontend Retry Logic

```typescript
// Add retry logic to ChatInterface.tsx
const sendMessageWithRetry = async (content: string, retries = 3) => {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(...)
      if (res.ok) return res.json()
    } catch (e) {
      if (i === retries - 1) throw e
      await sleep(1000 * (i + 1)) // Exponential backoff
    }
  }
}
```

---

## ✅ Validation Checklist

- [x] XML parser created (`src/shared/xml_parser.py`)
- [x] v3 router updated to use parser
- [x] Inline JSON stripped from display text
- [x] Metadata populated from XML tags
- [ ] Frontend shows clean conversation (no JSON)
- [ ] UI cards appear when metadata present
- [ ] Network error retry logic added (future)

---

## 📝 Key Insights

1. **LLM IS working correctly** - It's generating proper XML-tagged responses
2. **The bug is in the router** - Not parsing/stripping the XML
3. **Frontend expects parsed metadata** - Not raw LLM output
4. **7-step flow is sound** - Just needs proper response handling

---

**Status:** Fix implemented, ready for testing  
**Next Steps:** Test with real conversation, verify UI cards appear
