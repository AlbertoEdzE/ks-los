# Architectural Proposal: AI-Driven Agentic System for Loan Prequalification and Financial Advisory

**Prepared by:** Lead AI Architect & Systems Researcher
**Date:** February 2026
**Subject:** Conceptualization, Design, and Implementation Plan for the Next-Generation Credit Assessment Agent

---

## 1. Executive Summary

This document presents a comprehensive architectural proposal for the development of an advanced Agentic AI system tailored for loan prequalification and financial advisory. Based on the initial dialogue between stakeholders (Alberto and Andrea), the system is envisioned to bridge the gap between traditional, rigid credit bureau assessments and modern, dynamic financial advisory. 

By leveraging State-of-the-Art (SOTA) Multi-Agent architectures, alternative credit scoring (ACS) machine learning models, and Open Banking integrations, the proposed system will not only automate the risk assessment process but also provide prescriptive, personalized financial advice to applicants. This approach maximizes the probability of loan approval while democratizing access to credit, particularly for demographics with "thin" credit files.

## 2. System Conceptualization & Requirements Analysis

Based on the transcript analysis, the core requirements and conceptual pillars of the system are defined as follows:

### 2.1. Core Objectives
*   **Holistic Data Integration:** The system must aggregate data from traditional Credit Bureaus (Buró de Crédito) and transactional banking histories (deposits, account movements) to synthesize a 360-degree financial profile.
*   **Intelligent Prequalification:** Automate the assessment pipeline, dynamically analyzing an applicant's debts, assets (e.g., vehicles, real estate), and cash flow.
*   **Prescriptive Advisory (The "Agent" Factor):** Unlike traditional systems that output a binary "approved/denied," this system acts as a financial counselor. For marginal or declining cases, it must generate actionable recommendations (e.g., *"Delay your application by 3 months to increase account turnover,"* or *"Register your vehicle as collateral to reduce the risk profile"*).

## 3. State-of-the-Art (SOTA) Industry Context

Recent advancements in AI and Open Finance provide the technological landscape necessary to build this system:

*   **Open Banking & Open Finance in LatAm:** Regulatory frameworks across Latin America (e.g., Brazil, Mexico, Chile) are mandating Open Banking APIs. Providers like **Belvo** or **Prometeo** allow seamless, user-consented extraction of transactional data, solving the historical bottleneck of manual bank statement reviews.
*   **Agentic Frameworks:** The industry has evolved beyond single-prompt LLMs to Multi-Agent Systems (MAS). Frameworks like **LangGraph**, **Microsoft AutoGen**, and specialized financial platforms like **FinRobot** allow the creation of specialized "agents" that collaborate (e.g., a data analyst agent collaborating with a compliance agent).
*   **Alternative Credit Scoring (ACS):** SOTA predictive models (e.g., XGBoost, LightGBM) combined with Explainable AI (SHAP/LIME) are standard for compliant credit scoring. They assess "thin-file" customers by finding correlations in cash flow rather than relying solely on historical credit lines.

## 4. Architectural Approach: Local-First Multi-Agent System (MAS)

**Recommendation: Build a custom, local-first Multi-Agent System utilizing open-source foundational frameworks.**

While cloud-based APIs (e.g., OpenAI, Anthropic) are powerful, financial advisory systems handle highly sensitive PII and banking data. We recommend a **local-first approach** where the system dynamically configures its LLM backend:
*   **Primary Mode (Local via Ollama):** By default, the system will use **Ollama** to serve open-weights models locally. This guarantees absolute data privacy, as no customer financial telemetry leaves the internal infrastructure.
*   **Secondary Mode (Cloud API):** If specific API keys are provided via the environment configuration, the system can seamlessly route tasks to external SOTA models (GPT-4o, Claude 3.5), allowing flexibility based on the institution's risk appetite.

### Justification:
1.  **Data Privacy & Security:** Local inference completely eliminates the risk of third-party data breaches or non-compliance with banking data residency laws.
2.  **Configurable Flexibility:** Allows the embedding of custom banking logic locally, but can gracefully step up to cloud APIs if required and explicitly authorized.
3.  **Cost Efficiency:** Running local models via Ollama significantly reduces the variable costs associated with high-volume transactional LLM API calls.

## 5. Proposed System Architecture

Our proposal utilizes a **Multi-Agent System (MAS)** architecture, logically partitioned into three isolated layers:

### 5.1. Data Ingestion & Integration Layer
*   **Open Banking Gateway:** Integrates with aggregators (e.g., Belvo) to ingest real-time banking transactions, categorizing income and expenses.
*   **Credit Bureau API Subsystem:** Securely fetches traditional credit scores and historical debt profiles.
*   **Asset Registry Connector:** Verifies manually or automatically registered assets (vehicles, real estate) to assess collateral viability.

### 5.2. Cognitive Orchestration Layer (The Multi-Agent Core)
Built on **LangGraph**, this layer coordinates several specialized AI agents:
1.  **Data Synthesizer Agent:** Cleanses incoming data and builds a normalized vector profile of the user's financial health.
2.  **Risk & Decision Agent (Predictive Engine):** Utilizes traditional Machine Learning (XGBoost) combined with Explainable AI (XAI). It rapidly outputs a dynamic risk score and flags areas of concern (e.g., high debt-to-income ratio).
3.  **Advisory Agent (Generative Engine):** The core differentiator. An LLM (e.g., GPT-4o or Claude 3.5) equipped with Retrieval-Augmented Generation (RAG). It takes the output from the Risk Agent and queries an internal Vector Database of banking policies to generate human-readable, highly specific financial recommendations.
4.  **Compliance & Guardrail Agent:** A deterministic validation layer that intercepts the Advisory Agent's output to ensure no promises of credit are made and all advice complies with financial regulations.

### 5.3. Presentation Layer
*   **User Interface (Applicant):** A dynamic chat-based or web-form interface designed to guide the young applicant through the prequalification process.
*   **Agent Terminal Interface (Bank Executive):** A dashboard displaying the user's inferred risk profile, explanations of the AI's deductions, and suggested strategies, facilitating a hybrid "human-in-the-loop" approval process.

## 6. Technology Stack

| Domain | Recommended Technology | Rationale |
| :--- | :--- | :--- |
| **Agent Orchestration** | LangGraph (Python) | SOTA stateful multi-agent orchestration; excellent for cyclic AI reasoning. |
| **Local LLM (Default)** | Ollama (Llama 3.1 8B / Qwen 2.5 / Mixtral) | **Llama 3.1 8B:** Excellent balance of speed and instruction following. **Qwen 2.5:** Top-tier for numerical reasoning and JSON data extraction. **Mixtral 8x7B:** Great for complex, nuanced financial advisory logic. |
| **Cloud LLM (Fallback)** | GPT-4o / Claude 3.5 Sonnet | Used conditionally only if API keys are provided, for maximum reasoning overhead. |
| **Predictive Modeling** | XGBoost + SHAP | High performance for tabular financial data with mandatory explainability. |
| **Data Integrations** | FastAPI, Celery, Redis | Highly asynchronous backend to handle slow API calls to credit bureaus. |
| **Knowledge Base (RAG)** | Pinecone / Milvus | Vector database to store underwriting policies and product matrices. |
| **Open Banking API** | Belvo / Plaid | Leading LatAm/Global aggregators for extracting banking telemetry. |

## 7. Strategic Implementation Plan

To mitigate risk and ensure a successful rollout, an iterative Agile approach is recommended:

**Phase 1: Foundation & Data Normalization (Weeks 1-4)**
*   Establish secure connections to Credit Bureaus and Open Banking APIs.
*   Develop the Data Synthesizer Agent to normalize disparate data formats into a unified financial profile.

**Phase 2: Predictive Risk Engine (Weeks 5-8)**
*   Train and deploy the ML Risk Assessment models.
*   Implement SHAP-based Explainable AI to ensure transparency for regulatory audits.

**Phase 3: Cognitive Advisory Orchestration (Weeks 9-14)**
*   Develop the Advisory Agent utilizing LangGraph and RAG.
*   Ingest the institution's credit policy manuals into the vector database.
*   Implement the Compliance & Guardrail Agent.

**Phase 4: Interface Integration & Beta Testing (Weeks 15-18)**
*   Develop the terminal for bank executives and the applicant-facing prequalification portal.
*   Initiate a "Shadow Mode" deployment where the AI provides recommendations internally to loan officers before exposing it directly to consumers.

## 8. Conclusion

The transition from a reactive credit scoring system to a **proactive, agentic financial advisory system** represents a paradigm shift in loan origination. By unifying SOTA open-source AI orchestration with Open Banking data streams, this system will not only optimize risk underwriting but fundamentally enhance the customer lifecycle, driving both conversion rates and financial inclusion.
