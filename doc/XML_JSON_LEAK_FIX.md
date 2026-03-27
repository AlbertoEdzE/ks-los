# KS-LOS v3 Router: XML/JSON Leak Fix - Implementation Report

**Date:** March 26, 2026  
**Issue:** JSON and XML tags leaking into chat UI  
**Status:** ✅ **FIXED**

---

## 🐛 Problem Summary

### User-Facing Symptoms

From the screenshot provided by user:

1. **Inline JSON displayed in chat:**
   ```
   ... so we can find the most affordable option. { "purpose": "home_purchase" }
   ```

2. **Repeated JSON in assistant messages:**
   - Every message had trailing JSON objects
   - Made conversation look unprofessional and broken

3. **Metadata not populating UI cards:**
   - Loan snapshot cards not appearing
   - Recommendations not showing
   - Documents checklist not displaying

### Root Cause Analysis

**The LLM was working correctly** - generating proper XML-tagged responses:

```xml
That's wonderful! A home purchase is a major milestone.

<intent_analysis>
{"purpose": "home_purchase", "urgency": "high"}
</intent_analysis>
```

**The bug was in the v3 router** - it was returning the RAW LLM response without:
1. Stripping XML tags from display text
2. Parsing XML tags to extract metadata
3. Removing inline JSON objects

---

## ✅ Solution Implemented

### 1. Created XML Parser Module

**File:** `src/shared/xml_parser.py` (NEW - 206 lines)

**Key Functions:**

```python
def parse_llm_response(content: str) -> Tuple[str, Dict[str, Any]]:
    """
    Parse LLM response with XML-tagged structured data.
    
    Returns:
        - clean_text: For display (XML/JSON stripped)
        - metadata_dict: For UI cards (parsed from XML)
    """
```

**Features:**
- Extracts JSON from XML tags (`<intent_analysis>`, `<loan_snapshot>`, etc.)
- Strips XML tags from content
- Removes inline JSON objects (`{...}`)
- Converts snake_case tags to camelCase metadata keys
- Handles nested structures (intentAnalysis.intentSummary)

### 2. Updated v3 Router

**File:** `src/api/routers/v3_agentic_conversations_router.py` (MODIFIED)

**Changes:**

```python
# BEFORE (buggy):
assistant_message = {
    "content": response_text,  # Raw LLM output with XML/JSON
    "metadata": {...}  # Only state-based data
}

# AFTER (fixed):
# Parse XML from LLM response
clean_response_text, parsed_metadata = parse_llm_response(raw_response_text)

assistant_message = {
    "content": clean_response_text,  # Clean for display
    "metadata": parsed_metadata  # Parsed from XML
}
```

---

## 🧪 Testing Results

### Test 1: Intent Capture

**Input:**
```
User: "I want a home loan"
```

**Output:**
```json
{
  "response": "That's wonderful! A home purchase is a major milestone. To help me structure the best path for you, could you share more details? Specifically, I'd love to know what the property value or loan amount is, and what you're planning for a down payment so we can find the most affordable option.",
  "message": {
    "content": "That's wonderful! A home purchase is a major milestone...",
    "metadata": {
      "intentAnalysis": {
        "intentSummary": {
          "purpose": "home_purchase"
        }
      }
    }
  }
}
```

**✅ PASS:**
- Content is clean (no JSON/XML)
- Metadata properly populated
- Frontend can display clean text and use metadata for UI

### Test 2: Multi-Turn Conversation

**Conversation Flow:**
1. User: "I want a home loan"
2. Assistant: (asks for details)
3. User: "350000 usd, down payment 15%"
4. Assistant: (asks for employment)

**Result:**
- All messages clean (no JSON leaking)
- Metadata accumulated correctly
- State persisted to database

### Test 3: Full Validation Suite

```
✅ PASS: Backend Health Check
✅ PASS: V3 Create Conversation
✅ PASS: V3 Get Conversation
✅ PASS: V3 Send Message
✅ PASS: V3 Get Messages
✅ PASS: V3 Get Loan
✅ PASS: V3 State Persistence
✅ PASS: V3 Delete Conversation
✅ PASS: V2 Backward Compatibility (Phases)
✅ PASS: Intent Extraction

Passed: 10/10 (100.0%)
```

---

## 📊 Borrower Journey: 7-Step Flow (Documented)

### Mode 1: Advisory (Steps 1-4)

| Step | Name | Goal | Extracts | UI Components |
|------|------|------|----------|---------------|
| 1 | Intent Capture | Understand need | `purpose`, `borrower_name` | None |
| 2 | Financial Context | Employment & income | `employment_type`, `monthly_income` | None |
| 3 | Loan Details | Amount & debts | `loan_amount`, `existing_debts` | None |
| 3b | Contact Capture | Contact info | `email`, `phone` | None |
| 4 | Snapshot & Recommendations | Generate options | N/A (computes) | `LoanSnapshotCard`, `LoanCard` × 3 |

### Mode 2: Application (Steps 5-6)

| Step | Name | Goal | Generates | UI Components |
|------|------|------|-----------|---------------|
| 5 | Document Collection | Collect docs | `documents_checklist` | `DocumentsCard` |
| 6 | Application Submission | Submit & STP | `stp_processing` | `StpProcessingCard`, `AffordabilityCard` |

### Mode 3: Completion (Step 7)

| Step | Name | Goal | Generates | UI Components |
|------|------|------|-----------|---------------|
| 7 | Offer & Acceptance | Get signature | `terms_acceptance` | `TermsAcceptanceCard` |

---

## 🔧 Technical Details

### XML Tag Patterns Supported

```python
XML_PATTERNS = {
    "intent_analysis": ...,
    "loan_snapshot": ...,
    "loan_recommendations": ...,
    "documents_checklist": ...,
    "loan_application": ...,
    "stp_processing": ...,
    "terms_acceptance": ...,
    "phase_update": ...,
}
```

### Metadata Key Mapping

| XML Tag | Metadata Key | Frontend Usage |
|---------|-------------|----------------|
| `<intent_analysis>` | `intentAnalysis` | Intent summary |
| `<loan_snapshot>` | `loanSnapshot` | LoanSnapshotCard |
| `<loan_recommendations>` | `loanRecommendations` | LoanCard × N |
| `<documents_checklist>` | `documentsChecklist` | DocumentsCard |
| `<stp_processing>` | `stpProcessing` | StpProcessingCard |
| `<terms_acceptance>` | `termsAcceptance` | TermsAcceptanceCard |

### Inline JSON Removal

Regex patterns remove standalone JSON objects:
```python
# Remove { "key": "value" }
re.sub(r'\s*\{\s*"[^"]+"\s*:\s*"[^"]+"\s*\}\s*', ' ', cleaned)

# Remove { "key": [...] }
re.sub(r'\s*\{\s*"[^"]+"\s*:\s*\[[^\]]*\]\s*\}\s*', ' ', cleaned)
```

---

## 📁 Files Changed

### New Files (2)
1. `src/shared/xml_parser.py` (206 lines) - XML/JSON parsing
2. `doc/BORROWER_JOURNEY_FIX.md` - Analysis documentation
3. `doc/XML_JSON_LEAK_FIX.md` - This document

### Modified Files (1)
1. `src/api/routers/v3_agentic_conversations_router.py` (+20 lines) - Use XML parser

**Total Impact:** ~226 lines added

---

## 🎯 Before vs After

### Before (Buggy)

**Assistant Message Content:**
```
That's wonderful! A home purchase is a major milestone. To help me structure 
the best path for you, could you share more details? Specifically, I'd love 
to know what the property value or loan amount is, and what you're planning 
for a down payment so we can find the most affordable option. { "purpose": 
"home_purchase" }
```

**Metadata:**
```json
{
  "loan_snapshot": null,
  "recommendations": null,
  "documentsChecklist": null
}
```

### After (Fixed)

**Assistant Message Content:**
```
That's wonderful! A home purchase is a major milestone. To help me structure 
the best path for you, could you share more details? Specifically, I'd love 
to know what the property value or loan amount is, and what you're planning 
for a down payment so we can find the most affordable option.
```

**Metadata:**
```json
{
  "intentAnalysis": {
    "intentSummary": {
      "purpose": "home_purchase"
    }
  },
  "documentsChecklist": null,
  "application_id": null,
  "stp_status": "pending"
}
```

---

## ✅ Validation Checklist

- [x] XML parser created and tested
- [x] v3 router updated to use parser
- [x] Inline JSON stripped from display text
- [x] Metadata populated from XML tags
- [x] All 10 validation tests pass
- [x] State persistence still works
- [x] V2 backward compatibility maintained
- [x] Documentation created

---

## 🔮 Next Steps (Optional Enhancements)

1. **Frontend retry logic** - Handle network timeouts gracefully
2. **Streaming responses** - Show LLM output as it's generated
3. **Error messages** - Better user-facing error descriptions
4. **Loading indicators** - Show "AI is thinking..." during LLM calls
5. **Confidence visualization** - Show extraction confidence to users

---

## 📚 Related Documentation

- `doc/MIGRATION_STATUS_REPORT.md` - Overall migration status
- `doc/MIGRATION_IMPLEMENTATION_PLAN.md` - Implementation methodology
- `doc/BORROWER_JOURNEY_FIX.md` - Detailed borrower journey analysis
- `src/shared/xml_parser.py` - XML parser module (inline documentation)

---

**Status:** ✅ **COMPLETE**  
**Validation:** 10/10 tests passing  
**Production Ready:** Yes (for this specific issue)

---

**END OF REPORT**
