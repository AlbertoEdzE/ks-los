# Architectural Proposal v3: AI-Driven Agentic System for Loan Prequalification and Financial Advisory
## Caribbean Financial Institution Edition — Open-Source First, Evolutionary Architecture

**Prepared by:** Lead AI Architect & Systems Researcher
**Date:** February 2026
**Version:** 3.0 — Caribbean Context + Phased Open-Source Strategy
**Regulatory Context:** ECCB / ECCU | EveryData Credit Bureau | Payment System and Services Act 2025

---

## 1. Executive Summary

This is the third and definitive revision of the architectural proposal. It incorporates two major refinements:

**Caribbean Context:** This system is not built for Mexico. It is built for a Caribbean financial institution operating within the regulatory jurisdiction of the Eastern Caribbean Central Bank (ECCB) or a comparable Caribbean authority. The data landscape, credit bureau infrastructure, open banking maturity, and regulatory framework are fundamentally different — and in some ways, more open and forward-looking than LatAm peers.

**Open-Source First, Evolutionary Architecture:** The system is built from the ground up as a fully local, fully open-source stack. Every phase is functional and production-deployable on its own. Each subsequent phase *adds* capabilities as optional enrichment layers — activated only when external credentials and data sources are explicitly configured. No cloud dependency is ever required; it is always a choice.

This results in a system that can go live fast, in a small institution with modest infrastructure, and scale gracefully into a sophisticated multi-source AI platform as the institution's maturity grows.

---

## 2. Caribbean Regional Context

### 2.1. The Credit Bureau Landscape — EveryData ECCU

This is a critical distinction from the Mexico/LatAm context. The Caribbean credit bureau infrastructure is **brand new and still rolling out.**

- **EveryData ECCU Limited** was licensed by the ECCB as the official credit bureau for the Eastern Caribbean Currency Union (ECCU)
- **September 2024:** Antigua and Barbuda became the first country to go live
- **March 2025:** Expansion to Grenada, St. Lucia, and St. Vincent and the Grenadines
- **Remaining ECCU members** (St. Kitts & Nevis, Dominica, Montserrat, Anguilla) are onboarding progressively
- For **non-ECCU Caribbean** (Trinidad & Tobago, Jamaica, Dominican Republic, Barbados): separate bureaus exist — Caribbean Credit Bureau Ltd. (CCBL) in T&T, CRIF/JCB in Jamaica, DataCrédito in the DR

**Implication for architecture:** The system must be designed to operate gracefully when formal credit bureau data is sparse, incomplete, or unavailable for specific island territories. The **alternative credit scoring (open banking + behavioral signals) module is not a nice-to-have — it is the primary engine** for most of the target population. The system must be thin-file-first by design, not as an afterthought.

### 2.2. The Open Banking Landscape

Open Banking in the ECCU is nascent. The **Payment System and Services Act 2025 (PSSA)** — already passed in Antigua & Barbuda, Grenada, and St. Lucia — establishes the regulatory sandbox for fintech innovation, but mandated API standards are not yet in force region-wide.

**Implication:** Belvo and Prometeo (the LatAm open banking aggregators) have no ECCU coverage yet. **Data extraction in Phase 1 will primarily be bank-statement-based (PDF/CSV upload) or direct internal bank data.** Open banking API aggregators are a Phase 3+ integration when the regional infrastructure matures.

### 2.3. The Regulatory Environment

- **ECCB oversight** for ECCU members: Banking Amendment Bill 2024 introduces market conduct regulation and financial consumer protection
- **Data Protection:** A harmonized Data Protection and Privacy Bill is in development across ECCU — architecture must anticipate this by building privacy-first from day one
- **DCash (CBDC):** The ECCB's Eastern Caribbean Digital Currency is live. DCash transaction data is a potential future alternative credit signal
- **Tourism-heavy economies:** Credit demand is highly seasonal; risk models must account for income volatility linked to tourism cycles
- **Diaspora remittances:** A significant income source for many applicants — remittance data from Western Union, MoneyGram, and local agents should be treated as a first-class income signal in the thin-file model

### 2.4. Caribbean-Specific Credit Signals

| Signal | Mexico Equivalent | Caribbean Equivalent |
|---|---|---|
| IMSS Employment | ECCB payroll data (not yet aggregated) | NIS (National Insurance Scheme) contributions — most ECCU countries |
| SAT Fiscal / Tax | GRA (Govt Revenue Authority) filings | Limited API access; manual in most territories |
| Open Banking transactions | Belvo (mature) | Bank statement upload (Phase 1), future PSSA-compliant APIs |
| Remittances | Not a primary signal | **Primary income signal** for many thin-file applicants |
| Tourism seasonality | N/A | **Key cash flow modifier** — income regularity scoring must account for this |
| NIS contributions | IMSS | Direct proxy for formal employment and income level |

---

## 3. Architectural Philosophy: The Evolutionary Stack

The core design principle is: **every phase is a complete, working system. Later phases enrich it, never replace it.**

```
Phase 1: Open Core         → Fully local, zero external dependencies
          ↓ (adds)
Phase 2: Predictive Layer  → ML risk engine on top of Phase 1 data
          ↓ (adds)
Phase 3: Open Banking APIs → External data sources when available/configured
          ↓ (adds)
Phase 4: Cloud LLM Option  → Cloud model fallback when credentials provided
          ↓ (adds)
Phase 5: Full Ecosystem    → MCP, DCash signals, NIS API, regional expansion
```

Each phase is activated by **configuration, not code changes**. A `.env` file with empty values = Phase 1 behavior. Fill in credentials → higher phases activate automatically.

---

## 4. Phase 1: The Open Core (Weeks 1–8)
### *Fully local. Zero external API dependencies. Production-ready on day one.*

**This is the foundation everything else builds on. It must be excellent on its own.**

### 4.1. What Phase 1 Delivers

A functional loan prequalification system that:
- Accepts applicant data via a guided chat interface (in English, and optionally in Spanish/French Creole depending on territory)
- Processes bank statements (PDF/CSV upload) using local document parsing
- Consults the institution's internal data (existing customer relationship, deposit history)
- Applies a rules-based + basic ML prequalification engine
- Provides the Applicant Journey Coach conversation
- Outputs a risk narrative in plain English for loan officers
- Maintains a full audit log locally

### 4.2. Phase 1 Technology Stack (100% Open Source, 100% Local)

| Layer | Technology | Why |
|---|---|---|
| Agent Orchestration | **LangGraph** (Python) | Open source, Apache 2.0 license, production-grade stateful agents |
| Local LLM | **Ollama** running **Qwen2.5:14b** | Best open model for structured financial data extraction and JSON; fully local |
| Fallback LLM | **Ollama** running **Llama 3.1:8b** | Faster, lighter model for simple conversational coaching flows |
| Document Parsing | **Docling** (IBM, open source) | Extracts structured data from PDF bank statements with high accuracy |
| Database | **PostgreSQL** | Open source, battle-tested, stores all applicant profiles and audit logs |
| Vector Store (RAG) | **PGVector** (PostgreSQL extension) | RAG on top of existing PostgreSQL — no separate vector DB needed in Phase 1 |
| Predictive Model | **XGBoost** + **SHAP** | Open source; trained on internal bank data |
| Session/Cache | **Redis** | Open source; agent state and session management |
| API Layer | **FastAPI** | Open source; exposes agent endpoints to the UI |
| Applicant UI | **React** | Open source; chat interface |
| Executive Terminal | **React** dashboard | Loan officer view: risk profile, SHAP explanations, coaching history |
| Embeddings | **nomic-embed-text** (via Ollama) | Open source embedding model for RAG — runs locally |
| Observability | **LangSmith Community** (free tier) or **Langfuse** (self-hosted) | Agent tracing; Langfuse is fully self-hostable, open source |

### 4.3. Phase 1 Data Sources

```
┌─────────────────────────────────────────────┐
│           PHASE 1 DATA SOURCES              │
│                                             │
│  ✅ Internal Bank CRM                       │
│     Existing customer history, products,   │
│     deposit patterns, relationship depth   │
│                                             │
│  ✅ Bank Statement Upload (PDF/CSV)         │
│     Parsed by Docling locally              │
│     12-month transaction history           │
│     Income categorization                  │
│                                             │
│  ✅ Applicant Self-Declaration              │
│     Structured interview via Journey Coach │
│     Assets, liabilities, employment        │
│                                             │
│  ✅ RAG Knowledge Base                     │
│     Bank's credit policies (internal docs) │
│     Product catalog, collateral guidelines │
│     Ingested into PGVector                 │
└─────────────────────────────────────────────┘
```

### 4.4. Phase 1 Agent Architecture

```
Applicant Chat UI
      │
      ▼
┌─────────────────┐
│ Agent 1:        │   Conversational pre-application coaching.
│ Journey Coach   │   Extracts soft profile. No external API calls.
│ (Local Ollama)  │   Outputs: Readiness Score + Coaching Plan
└────────┬────────┘
         │ (if applicant decides to proceed formally)
         ▼
┌─────────────────┐
│ Agent 2:        │   Parses uploaded bank statements (Docling).
│ Data            │   Fetches internal CRM data.
│ Synthesizer     │   Builds ApplicantFinancialProfile JSON.
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Agent 3:        │   XGBoost on ApplicantFinancialProfile.
│ Risk Engine     │   Outputs: Risk Score + SHAP explanation.
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Agent 4:        │   LLM (local Qwen2.5) + RAG over bank policies.
│ Advisory Agent  │   Generates plain-English recommendation.
│ (RAG)           │   Dual output: applicant summary + officer JSON.
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Agent 5:        │   Rule-based validation. No credit promises.
│ Compliance      │   ECCB consumer protection rules.
│ Guardrail       │   Logs everything to PostgreSQL audit table.
└────────┬────────┘
         │
         ▼
Executive Terminal (Loan Officer Dashboard)
Human-in-the-Loop approval gate
```

### 4.5. Caribbean-Specific Adjustments in Phase 1 Model

The XGBoost model in Phase 1 is trained with Caribbean-specific feature engineering:

- **Tourism Seasonality Coefficient:** Income regularity is scored against a regional tourism calendar. Reduced income in off-season is not penalized if the pattern is consistent year-over-year
- **Remittance Recognition:** Bank statement parsing flags recurring inbound international transfers as a stable income category (not random deposits)
- **NIS Declaration Proxy:** Applicants who declare NIS contributions in the structured interview receive an employment verification proxy score
- **Multi-territory Currency Handling:** XCD, JMD, TTD, USD, BBD — all normalized to USD equivalent for cross-territory comparability

---

## 5. Phase 2: Predictive Layer Enhancement (Weeks 9–14)
### *Still fully local. Adds ML sophistication and thin-file population models.*

**Triggered by:** Sufficient internal data accumulated from Phase 1 operations (~3–6 months of applications).

### 5.1. What Phase 2 Adds

- **Separate thin-file XGBoost model** trained specifically on applicants with no prior credit bureau history (uses behavioral signals from bank statements as primary features)
- **Automatic population segmentation:** Data Synthesizer detects which model to route to (full-file vs. thin-file) based on credit bureau data availability
- **Champion/Challenger model evaluation:** Two models run in parallel; loan officers see which model flagged a given application, enabling ongoing model validation
- **Drift detection:** Automated alerts when model performance degrades, especially important given tourism seasonality causing distribution shifts

### 5.2. New Phase 2 Technology

| Addition | Technology | Notes |
|---|---|---|
| ML experiment tracking | **MLflow** (self-hosted) | Open source; tracks model versions, metrics, feature importance |
| Model monitoring | **Evidently AI** (open source) | Data drift, feature drift, model performance monitoring |
| Thin-file model | **XGBoost** (separate instance) | Trained on behavioral/bank-statement features only |

---

## 6. Phase 3: External Data Enrichment (Weeks 15–22)
### *Open-source core unchanged. Adds external integrations when credentials are provided.*

**Triggered by:** Institution configures external API credentials in `.env`.  
**Default behavior without credentials:** System continues running Phase 1+2 with no degradation.

### 6.1. Integration Adapter Architecture

Each external source is wrapped in a **local MCP (Model Context Protocol) server**. This standardizes how agents access external data — all calls are audited, consent-scoped, and OAuth 2.1 authenticated regardless of the data source.

If no credentials are present, the MCP adapter returns an empty response and the agent falls back to available local data. **This is the key design pattern that makes the stack evolutionary.**

```python
# Example: Agent behavior is credential-aware
profile = await data_synthesizer.build_profile(applicant_id)
# → If EVERYDATA_API_KEY is set: fetches credit bureau data
# → If not set: marks credit_bureau_data as "unavailable", 
#               increases weight of behavioral signals
# → Either way: produces a valid ApplicantFinancialProfile
```

### 6.2. Phase 3 External Integrations

| Source | Credential Required | What It Provides | Caribbean Availability |
|---|---|---|---|
| **EveryData ECCU** | `EVERYDATA_API_KEY` | Official ECCU credit bureau data | Live in Antigua, Grenada, St. Lucia, SVG (2025) |
| **Caribbean Credit Bureau Ltd. (CCBL)** | `CCBL_API_KEY` | Trinidad & Tobago credit history | Available (T&T) |
| **CreditInfo Jamaica** | `CREDITINFO_JM_KEY` | Jamaica credit bureau | Available |
| **National Insurance (NIS)** | `NIS_API_KEY` (territory-specific) | Employment verification, contribution history | API availability varies by territory |
| **Bank Statement Aggregator** | `AGGREGATOR_KEY` | Automated bank statement pull (where PSSA-compliant APIs exist) | Emerging; Antigua & Barbuda, St. Lucia pilot |
| **Remittance Data** | `REMITTANCE_PARTNER_KEY` | Western Union / MoneyGram verified income | Partnership-based; institution negotiates directly |

### 6.3. EveryData ECCU Integration (Primary Credit Bureau)

EveryData ECCU is the strategic credit bureau integration for ECCU-region institutions. As the ECCB-licensed operator expanding across all 8 ECCU member states, it becomes the definitive credit history source for the region.

Integration approach:
- Consent-first: applicant provides explicit written/digital consent before any bureau query
- Query only at formal application stage (Journey Coach phase never queries the bureau — preserves applicant score)
- Store bureau response locally in PostgreSQL (encrypted, consent-tagged)
- Thin-file flag: if bureau returns "no record found," system automatically routes to thin-file model

---

## 7. Phase 4: Cloud LLM Option (Weeks 23–26)
### *Local LLM remains default. Cloud activates only when API key is present.*

**Triggered by:** Institution provides `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in `.env`.  
**Default behavior without keys:** Ollama continues as the LLM backend. No change in system behavior.

### 7.1. What Phase 4 Adds

When a cloud API key is present, specific agents can be configured to route complex tasks to cloud models while keeping simpler tasks on local models:

```yaml
# config/llm_routing.yaml
agents:
  journey_coach: ollama/qwen2.5:14b        # Always local (sensitive PII conversation)
  data_synthesizer: ollama/qwen2.5:14b     # Always local (processes raw financial data)
  risk_engine: deterministic               # Always local (XGBoost, no LLM)
  advisory_agent:
    default: ollama/qwen2.5:14b            # Local by default
    if_cloud_key_present: claude-sonnet-4  # Upgrade to cloud for complex narratives
  compliance_guardrail: deterministic      # Always local (rule-based)
```

**Why the Advisory Agent is the right place for cloud LLM:**
- It is the output-facing agent — quality of narrative matters most here
- It does NOT receive raw PII or transaction data — only the synthesized risk score and SHAP factors
- Cloud model sees: `{"risk_score": 0.38, "top_factors": ["low_income_regularity", "high_rent_ratio"], "product": "personal_loan_XCD_15000"}` — not account numbers or raw statements

### 7.2. Cloud LLM Options (When Configured)

| Provider | Model | Strength | Notes |
|---|---|---|---|
| Anthropic | **Claude Sonnet 4** | Best advisory narrative quality, nuanced financial language | Recommended |
| OpenAI | GPT-4o | Strong reasoning, broad capability | Alternative |
| Local upgrade | **Mixtral 8x7B via Ollama** | If institution prefers to invest in better local hardware | Higher VRAM requirement |

---

## 8. Phase 5: Full Ecosystem Integration (Month 7+)
### *The mature state. Everything connected, everything optional.*

**Triggered by:** Institutional maturity, regulatory alignment, partner agreements in place.

### 8.1. What Phase 5 Adds

- **DCash (CBDC) transaction signals:** For applicants transacting in the ECCB's Eastern Caribbean Digital Currency, on-chain activity becomes an alternative credit signal — directly verifiable, tamper-proof income and payment history
- **MCP-native integrations:** All data sources are now formally MCP servers, enabling any future AI tool (internal or partner) to consume the same data surfaces through a standardized protocol
- **Multi-territory deployment:** Single codebase deployed across multiple island territories, each with its own configuration (currency, regulatory rules, credit bureau endpoint, language preference)
- **Feedback loop:** Approved loan performance data feeds back into model retraining (closed-loop learning)
- **WhatsApp / SMS channel:** Journey Coach accessible via WhatsApp Business API for applicants without smartphones — critical for financial inclusion in rural and lower-income communities
- **Regulatory reporting automation:** Automated ECCB-compliant reporting on AI-assisted credit decisions (consumer protection requirements of the Banking Amendment Bill 2024)

### 8.2. Phase 5 Technology Additions

| Addition | Technology | Notes |
|---|---|---|
| MCP servers (formal) | Custom MCP adapters per data source | Replaces Phase 3 raw API wrappers |
| DCash signals | ECCB CBDC API (when available) | Future integration; architecture ready now |
| Multi-territory config | **Dynaconf** (Python) | Environment-aware configuration management |
| WhatsApp channel | **Twilio / Meta Business API** | External credential required; off by default |
| Feedback loop | **Airflow** (self-hosted) | Scheduled retraining pipeline |

---

## 9. Configuration Philosophy: The `.env` Gateway

The entire phase progression is controlled through environment configuration. No code changes required to move between phases.

```bash
# .env — Phase 1 (Open Core, Fully Local)
OLLAMA_HOST=http://localhost:11434
OLLAMA_PRIMARY_MODEL=qwen2.5:14b
OLLAMA_FAST_MODEL=llama3.1:8b
DATABASE_URL=postgresql://localhost/prequalification
REDIS_URL=redis://localhost:6379

# .env — Phase 3 additions (uncomment to activate)
# EVERYDATA_API_KEY=
# CCBL_API_KEY=
# NIS_API_KEY=
# REMITTANCE_PARTNER_KEY=

# .env — Phase 4 additions (uncomment to activate)
# ANTHROPIC_API_KEY=
# OPENAI_API_KEY=

# .env — Phase 5 additions (uncomment to activate)
# WHATSAPP_BUSINESS_TOKEN=
# DCASH_API_KEY=
# TWILIO_ACCOUNT_SID=
```

System startup logs clearly indicate which integrations are active:
```
[STARTUP] LLM Backend: Ollama (qwen2.5:14b) — Cloud LLM: NOT CONFIGURED
[STARTUP] Credit Bureau: EveryData ECCU — ACTIVE ✓
[STARTUP] NIS Integration: NOT CONFIGURED — thin-file model will be primary
[STARTUP] Cloud Advisory: NOT CONFIGURED — local Qwen2.5 will handle advisory
[STARTUP] WhatsApp Channel: NOT CONFIGURED
```

---

## 10. Full Technology Stack Summary

| Domain | Phase 1 (Default) | Phase 3+ (If Configured) |
|---|---|---|
| Agent Orchestration | LangGraph (open source) | ← Same |
| LLM | Ollama + Qwen2.5:14b | + Claude Sonnet 4 / GPT-4o (advisory only) |
| Embeddings | nomic-embed-text (Ollama) | ← Same |
| Document Parsing | Docling (IBM open source) | ← Same + Belvo/aggregator APIs |
| Database | PostgreSQL | ← Same |
| Vector Store | PGVector | + Milvus (Phase 5, if scale requires) |
| Predictive Model | XGBoost + SHAP | ← Same (two model variants) |
| ML Tracking | MLflow (self-hosted) | ← Same |
| Model Monitoring | Evidently AI (open source) | ← Same |
| Credit Bureau | Manual/internal only | + EveryData ECCU, CCBL, CreditInfo JM |
| Open Banking | Bank statement upload | + PSSA-compliant APIs (Phase 5) |
| Session/Cache | Redis | ← Same |
| API Layer | FastAPI | ← Same |
| Observability | Langfuse (self-hosted) | ← Same |
| Integration Protocol | FastAPI adapters | + MCP servers (Phase 5) |
| Async Tasks | Celery | ← Same |
| Channels | Web chat | + WhatsApp / SMS (Phase 5) |

**Minimum Infrastructure for Phase 1:**
A single server with 32GB RAM, a modern CPU (no GPU required for Qwen2.5:14b on CPU), and 500GB SSD is sufficient. GPU (RTX 3090 or better) makes inference significantly faster but is not required.

---

## 11. Revised Implementation Timeline

### Phase 1 — Open Core (Weeks 1–8)
- Week 1–2: Infrastructure setup (PostgreSQL, Redis, Ollama, LangGraph)
- Week 3–4: Document parsing pipeline (Docling + bank statement normalization)
- Week 5–6: Data Synthesizer Agent + basic XGBoost model (trained on internal data)
- Week 7: Advisory Agent (local LLM + RAG on internal policies), Compliance Agent
- Week 8: Journey Coach Agent + applicant UI + executive terminal
- **→ Phase 1 Go-Live: functional prequalification system, zero external dependencies**

### Phase 2 — Predictive Enhancement (Weeks 9–14)
- Thin-file XGBoost model training and validation
- MLflow experiment tracking setup
- Evidently AI monitoring setup
- Champion/Challenger model routing
- **→ Phase 2 Go-Live: improved accuracy, especially for thin-file applicants**

### Phase 3 — External Data (Weeks 15–22)
- EveryData ECCU integration (for applicable territories)
- CCBL / CreditInfo JM integration (for T&T / Jamaica if applicable)
- NIS data integration (territory-by-territory)
- Remittance income recognition module
- MCP adapter framework (preparation for Phase 5)
- **→ Phase 3 Go-Live: richer credit signals, higher approval rate accuracy**

### Phase 4 — Cloud LLM Option (Weeks 23–26)
- Cloud LLM routing configuration
- A/B evaluation: local vs. cloud advisory narrative quality
- Institution decides whether to maintain cloud key or remain fully local
- **→ Phase 4 Go-Live: optional enhanced advisory narrative quality**

### Phase 5 — Full Ecosystem (Month 7+)
- WhatsApp / SMS channel (financial inclusion outreach)
- DCash signal integration (when ECCB API available)
- Formal MCP server implementations
- Multi-territory configuration management
- Automated ECCB regulatory reporting
- Feedback loop: loan performance → model retraining
- **→ Phase 5 Go-Live: mature, multi-channel, self-improving system**

---

## 12. Success Metrics (Caribbean-Calibrated)

| Metric | Baseline | Phase 1 Target | Phase 3 Target |
|---|---|---|---|
| Prequalification time | Days (manual) | < 30 minutes | < 10 minutes |
| Thin-file approval rate | ~10–15% (limited bureau data) | +10 pts (behavioral scoring) | +25 pts (bureau + NIS + remittance) |
| Loan officer time per application | ~60 minutes | < 15 minutes | < 5 minutes |
| Journey Coach coaching conversion | N/A | > 30% return to apply | > 45% return to apply |
| Seasonal model accuracy | N/A | Baseline established | +15% accuracy vs. flat models |
| Audit compliance preparation | Manual (days) | Automatic (PostgreSQL logs) | Automatic + ECCB-formatted reports |

---

## 13. Conclusion

The Caribbean context changes this system in three fundamental ways. First, the credit bureau infrastructure is new and still rolling out — **EveryData ECCU** (the official ECCU bureau, live since September 2024) is the strategic integration, but thin-file behavioral scoring must be the primary engine, not a fallback. Second, Caribbean-specific income signals — **remittances, NIS contributions, and tourism-seasonal cash flows** — must be treated as first-class credit evidence. Third, the regulatory environment under the ECCB and the new **Payment System and Services Act 2025** is actually progressive and sandbox-friendly, creating room for this system to pioneer responsible AI-assisted credit in the region.

The open-source-first, evolutionary architecture ensures the institution can start delivering value immediately with Phase 1 — running fully local with zero external dependency — and grow the system's intelligence and data richness phase by phase, adding only what is needed, when it is needed, with explicit configuration decisions at every step.

The final mature system is not just a prequalification tool. It is a regional financial inclusion platform — designed to extend credit to the young, the self-employed, the remittance-dependent, and the seasonally employed workers who form the backbone of Caribbean economies, and who have historically been invisible to rigid credit scoring systems.

---

*Document reflects Caribbean regulatory context as of February 2026. EveryData ECCU status and PSSA 2025 adoption verified against ECCB publications. Technology choices verified against 2025–2026 open source ecosystem state.*