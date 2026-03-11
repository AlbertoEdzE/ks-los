# Project Ontology Definition

**Document ID:** ONT-001
**Version:** 1.0
**Phase:** 0.1
**Status:** Draft
**Last Updated:** February 2026

---

## 1. Purpose and Scope

This document establishes the foundational ontology for the AI-Driven Agentic System for Loan Prequalification and Financial Advisory. The ontology defines the complete taxonomy of the system, including the five core agents, their bounded contexts, input and output contracts, component inventories, and integration touchpoints. This document serves as the authoritative reference for all development activities, ensuring consistent understanding across all agents and team members throughout the project lifecycle.

The ontology presented herein is designed to support the Caribbean financial institution context, specifically addressing the requirements of the Eastern Caribbean Currency Union (ECCU) region. The system must handle multiple territories, diverse credit profiles, local regulatory requirements, and the unique economic patterns of small island economies. Every component defined in this ontology has been carefully considered against these regional requirements.

---

## 2. System Overview

### 2.1 High-Level Architecture

The system consists of five specialized AI agents that collaborate through a central orchestration layer. Each agent operates as an independent bounded context with specific responsibilities, yet all agents share common data schemas and communication protocols that enable seamless information flow. The architecture follows a hub-and-spoke model where the orchestration layer manages workflow sequencing, state management, and cross-agent coordination.

The five agents are organized around the core loan prequalification workflow. The Journey Coach Agent initiates contact with applicants and guides them through the application process. The Data Synthesizer Agent manages all data acquisition and normalization, including the critical Synthetic Credit Data Generator (SCDG) that enables development without live credit bureau connectivity. The Risk Engine Agent evaluates creditworthiness using machine learning models. The Advisory Agent generates personalized recommendations using retrieval-augmented generation. The Compliance Guardrail Agent ensures all outputs meet regulatory requirements.

### 2.2 Operational Context

The system operates in three distinct modes that reflect real-world deployment scenarios. In Development Mode, all credit data is generated synthetically using the SCDG, enabling full system development and testing without requiring live credit bureau connections. In Hybrid Mode, some territories have live bureau connectivity while others rely on synthetic data, reflecting the phased rollout of EveryData ECCU services across the Caribbean. In Full Live Mode, all territories are served by real credit bureau data, with the SCDG retained only for testing and disaster recovery purposes.

This operational flexibility requires the ontology to treat synthetic and real data sources as interchangeable from the perspective of downstream agents. The data pipeline architecture ensures that regardless of the source, all agents receive data in the same format with the same guarantees of completeness and validity.

---

## 3. Agent Definitions

### 3.1 Journey Coach Agent

The Journey Coach Agent serves as the primary interface between the applicant and the loan prequalification system. This agent manages all conversational interactions, guiding applicants through the application process while collecting necessary information and providing updates on their application status. The Journey Coach operates entirely on open data and publicly available information, never querying credit bureau data directly.

The bounded context of the Journey Coach Agent encompasses the complete applicant-facing workflow. This includes initial greeting and eligibility assessment, document collection and verification requests, application progress updates, notification delivery for decisions, and handling of applicant inquiries and support requests. The agent maintains session state throughout the application process, tracking which documents have been submitted, which questions have been answered, and what additional information is required before the application can proceed to underwriting.

**Input Contracts:**

The Journey Coach Agent receives input in the form of user messages through the applicant chat interface. These messages may be free-text questions, document upload acknowledgments, or structured responses to agent prompts. The agent also receives system events indicating changes in application state, such as document verification completion or risk assessment availability. The agent has access to the applicant's session context, including demographic information collected during onboarding, documents submitted, and conversation history.

**Output Contracts:**

The Journey Coach Agent produces conversational responses delivered through the applicant chat interface. These responses include questions to gather required information, explanations of document requirements, status updates on application progress, and notifications of next steps. The agent also produces workflow commands that update the application state, trigger downstream processes, and manage the overall application lifecycle. All outputs include appropriate metadata for logging, auditing, and analytics purposes.

### 3.2 Data Synthesizer Agent

The Data Synthesizer Agent is the central data management component of the system. This agent is responsible for acquiring, validating, normalizing, and transforming all data used in the loan prequalification process. The agent manages multiple data sources including credit bureau services, bank statement processors, and internal banking systems. Critically, the Data Synthesizer includes the Synthetic Credit Data Generator (SCDG), which produces statistically realistic credit profiles when live bureau data is unavailable.

The bounded context of the Data Synthesizer Agent encompasses the entire data pipeline. This includes the Credit Bureau Source Adapter that routes requests between live bureau services and the SCDG, the Bank Statement Adapter that processes PDF and CSV statements using Docling, the Internal Bank Adapter that retrieves CRM and deposit history, and the data normalization layer that transforms all inputs into the standardized ApplicantCreditProfile schema. The agent maintains data quality through validation gates, completeness checks, and consistency verification.

**Input Contracts:**

The Data Synthesizer Agent receives requests for applicant credit profiles through its internal API. These requests include the applicant's consent token, territory code, and optional parameters for specifying data source preferences. For bank statement processing, the agent receives uploaded documents with associated metadata. For internal bank data, the agent receives customer identifiers with appropriate authorization.

**Output Contracts:**

The Data Synthesizer Agent produces ApplicantCreditProfile documents in the standardized internal schema. These profiles include identity information, credit summary statistics, detailed payment behavior analysis, individual trade line records, inquiry history, and risk flags. Every profile includes metadata indicating the data source, whether synthetic or live, enabling downstream agents to apply appropriate confidence levels. The agent also produces data quality reports documenting any validation issues or completeness concerns.

### 3.3 Risk Engine Agent

The Risk Engine Agent evaluates creditworthiness using machine learning models trained on historical loan performance data. This agent produces risk scores, probability of default estimates, and loss given default assessments that inform lending decisions. The Risk Engine operates on the normalized credit profiles produced by the Data Synthesizer, applying XGBoost models with SHAP explanations to generate transparent, defensible risk assessments.

The bounded context of the Risk Engine Agent encompasses all credit risk evaluation activities. This includes feature engineering from credit profile data, model inference for risk scoring, SHAP value calculation for feature importance analysis, risk segmentation and cohort analysis, and model performance monitoring. The agent supports multiple model variants, including a standard model for applicants with credit bureau history and a specialized thin-file model for applicants with limited credit history.

**Input Contracts:**

The Risk Engine Agent receives ApplicantCreditProfile documents from the Data Synthesizer. These profiles must include the complete set of fields defined in the internal schema, including credit summary statistics, payment behavior indicators, trade line details, and inquiry history. The agent also receives configuration parameters specifying which model variant to use and what output format is required.

**Output Contracts:**

The Risk Engine Agent produces RiskAssessment documents containing the primary risk score (300-850 FICO-equivalent scale), probability of default estimate, loss given default assessment, risk tier classification (Prime, Near-Prime, Subprime, Deep Subprime), key risk factors identified through SHAP analysis, model confidence interval, and model version information. All assessments include complete audit trails documenting the input data, model version, and calculation parameters.

### 3.4 Advisory Agent

The Advisory Agent generates personalized recommendations and explanations for applicants using large language models augmented with retrieval-augmented generation (RAG). This agent produces natural language narratives that explain credit findings, justify risk assessments, and provide actionable recommendations for improving creditworthiness. The agent has access to product knowledge bases, regulatory guidelines, and best practices documentation.

The bounded context of the Advisory Agent encompasses all advisory and explanatory functions. This includes generating prequalification decision explanations, creating personalized credit improvement recommendations, producing loan product suggestions tailored to applicant profiles, explaining risk factors in accessible language, and generating compliance-required disclosures. The agent operates in both local LLM mode (Ollama with Qwen2.5:14b) and cloud LLM mode (when API keys are configured) to balance privacy, cost, and capability requirements.

**Input Contracts:**

The Advisory Agent receives RiskAssessment documents from the Risk Engine Agent and ApplicantCreditProfile documents from the Data Synthesizer. These inputs enable the agent to generate contextually accurate recommendations based on both the applicant's credit situation and the risk evaluation. The agent also receives configuration parameters specifying output length, tone, and language preferences.

**Output Contracts:**

The Advisory Agent produces AdvisoryReport documents containing decision explanations in accessible language, prioritized recommendations for credit improvement, suggested loan products with estimated terms, key risk factors with plain-language explanations, and any required regulatory disclosures. All reports include citations to the source data and model outputs that support the recommendations.

### 3.5 Compliance Guardrail Agent

The Compliance Guardrail Agent ensures that all system outputs meet regulatory requirements and internal policy constraints. This agent validates that recommendations comply with fair lending laws, reviews all communications for compliance with advertising regulations, and maintains audit trails required for regulatory examinations. The agent acts as a final checkpoint before any output reaches the applicant or loan officer.

The bounded context of the Compliance Guardrail Agent encompasses all compliance validation activities. This includes fair lending compliance checks (adverse action notices, disparate impact analysis), communication compliance review (advertising truthfulness, required disclosures), data privacy validation (consent verification, data minimization), audit trail maintenance, and regulatory reporting support. The agent maintains a rules engine that encodes current regulatory requirements and can be updated as regulations change.

**Input Contracts:**

The Compliance Guardrail Agent receives AdvisoryReport documents from the Advisory Agent, RiskAssessment documents from the Risk Engine Agent, and communication drafts from the Journey Coach Agent. These inputs represent all outputs that require compliance validation before reaching external recipients.

**Output Contracts:**

The Compliance Guardrail Agent produces ComplianceValidation documents containing validation status (approved, rejected, requires review), specific compliance issues identified (if any), required modifications (if rejected), and audit trail entries documenting the validation decision. For rejected outputs, the agent provides specific guidance on what changes are required to achieve compliance.

---

## 4. Component Inventory

### 4.1 Journey Coach Components

The Journey Coach Agent consists of the following technical components. The Conversation Manager handles dialogue state, context tracking, and response generation. The Workflow Orchestrator manages the application lifecycle, including state transitions and task sequencing. The Document Request Handler generates document collection requests and tracks submission status. The Notification Service delivers application updates through appropriate channels. The Session Store maintains conversation history and contextual information across interaction sessions.

Each component is implemented as an independent module with well-defined interfaces. The Conversation Manager exposes methods for processing incoming messages, generating responses, and managing dialogue state. The Workflow Orchestrator provides APIs for advancing application state, retrieving current state, and handling workflow events. The components communicate through internal message passing, with the orchestration layer coordinating interactions between components.

### 4.2 Data Synthesizer Components

The Data Synthesizer Agent consists of the following technical components. The Credit Bureau Source Adapter implements the routing logic between live bureau services and the SCDG based on territory configuration. The Synthetic Credit Data Generator (SCDG) produces statistically realistic credit profiles using Metro 2-compliant data structures. The SCDG includes the Profile Archetype Selector that maps applicant characteristics to appropriate credit profile types, the Markov Chain Generator that produces realistic payment history sequences, and the Validation Gate that validates output against Moov-IO Metro 2 standards.

The Bank Statement Adapter processes uploaded bank statements using Docling for PDF extraction and custom parsing logic for CSV formats. The Internal Bank Adapter retrieves customer data from internal banking systems through secure API connections. The Data Normalizer transforms all input data into the standardized ApplicantCreditProfile schema. The Data Quality Validator performs completeness checks, consistency verification, and anomaly detection on all data products.

### 4.3 Risk Engine Components

The Risk Engine Agent consists of the following technical components. The Feature Engineering module transforms raw credit profile data into model-ready features. The Model Inference Engine executes XGBoost models for risk scoring. The SHAP Calculator computes feature importance explanations for each assessment. The Model Registry manages multiple model variants and their deployment status. The Performance Monitor tracks model accuracy and drift metrics.

The feature engineering module implements approximately 200 derived features including utilization ratios, payment behavior patterns, credit depth indicators, and inquiry frequency metrics. The model inference engine supports both batch processing for model retraining and real-time inference for production scoring. The SHAP Calculator produces both local explanations (for individual applicant explanations) and global feature importance (for model monitoring).

### 4.4 Advisory Components

The Advisory Agent consists of the following technical components. The RAG Engine manages document retrieval from knowledge bases. The Prompt Manager constructs LLM prompts with appropriate context and constraints. The Response Generator produces natural language outputs using either local or cloud LLM backends. The Explanation Builder translates technical risk factors into accessible language. The Recommendation Prioritizer ranks suggestions by impact and feasibility.

The RAG Engine maintains vector embeddings of product documentation, regulatory guidelines, and best practices. The embedding model (nomic-embed-text through Ollama) produces context vectors that enable semantic retrieval of relevant information. The Prompt Manager ensures consistent prompt construction while allowing customization for different output requirements.

### 4.5 Compliance Components

The Compliance Guardrail Agent consists of the following technical components. The Rules Engine encodes current regulatory requirements as executable validation logic. The Fair Lending Validator performs adverse action analysis and disparate impact checks. The Communication Reviewer validates all outbound messages for compliance. The Audit Logger records all validation decisions with complete context. The Reporting Generator produces regulatory reports required by ECCB and local authorities.

The Rules Engine supports declarative rule definition, enabling compliance officers to add or modify rules without code changes. Rules are organized by regulation (ECCB Guidelines, Fair Credit Reporting Act, local consumer protection laws) and by product type (personal loans, mortgages, credit cards).

---

## 5. Integration Touchpoints

### 5.1 Synchronous Interfaces

Synchronous request-response interfaces are used when immediate feedback is required for workflow continuation. The primary synchronous interfaces are defined as follows.

The Journey Coach to Data Synthesizer interface retrieves applicant credit profiles on demand. The Journey Coach sends a profile request including applicant consent token and territory code. The Data Synthesizer returns a complete ApplicantCreditProfile or an error indicating why the profile could not be generated. This interface uses a 30-second timeout with automatic retry using exponential backoff (maximum 3 retries).

The Journey Coach to Risk Engine interface triggers risk assessment after credit profile retrieval. The Journey Coach sends the ApplicantCreditProfile to the Risk Engine. The Risk Engine returns a RiskAssessment with score, factors, and explanations. This interface uses a 60-second timeout to accommodate model inference time.

The Journey Coach to Advisory interface requests recommendation generation after risk assessment. The Journey Coach sends both the ApplicantCreditProfile and RiskAssessment to the Advisory Agent. The Advisory Agent returns an AdvisoryReport with recommendations. This interface uses a 120-second timeout to accommodate LLM inference time.

The Journey Coach to Compliance interface validates all outputs before delivery. The Journey Coach sends advisory reports and communication drafts to the Compliance Guardrail. The Compliance Guardrail returns validation decisions with any required modifications. This interface uses a 10-second timeout as compliance validation is a fast operation.

### 5.2 Asynchronous Events

Asynchronous event streaming is used for loose coupling between components where immediate response is not required. The primary asynchronous events are defined as follows.

The Document Received event is published by the Data Synthesizer when a bank statement is successfully processed. Subscribers include the Journey Coach (to update applicant status) and the Risk Engine (to trigger reassessment if previously scored). Events include document ID, applicant ID, processing status, and any issues identified.

The Profile Generated event is published by the Data Synthesizer when a new credit profile is created (either synthetic or live). Subscribers include the Risk Engine (to trigger initial assessment) and Analytics (for monitoring). Events include profile ID, applicant ID, source type (synthetic or live), and profile summary statistics.

The Assessment Completed event is published by the Risk Engine when a risk assessment finishes. Subscribers include the Advisory Agent (to generate recommendations), the Journey Coach (to update status), and Analytics (for monitoring). Events include assessment ID, applicant ID, risk score, and model version.

The Advisory Generated event is published by the Advisory Agent when a recommendation report is complete. Subscribers include the Compliance Guardrail (to validate before delivery), the Journey Coach (to deliver to applicant), and Analytics (for monitoring). Events include report ID, applicant ID, and report summary.

### 5.3 Shared State Coordination

Shared state coordination is used when multiple agents require access to common resources with consistency guarantees. The primary shared state resources are defined as follows.

The Applicant Session State is maintained in Redis with the applicant ID as the key. This state includes conversation history, collected information, submission status, and current workflow stage. Distributed locks prevent concurrent modifications during critical transitions (such as advancing workflow stages or triggering assessments).

The Credit Profile Cache caches generated profiles in Redis to avoid redundant generation. Cache entries expire after 24 hours or upon applicant request. Cache invalidation uses write-through strategy when profiles are regenerated.

The Assessment History maintains a complete history of all risk assessments for each applicant. This history is stored in PostgreSQL with append-only semantics. The history enables audit trails, model training data collection, and dispute resolution.

---

## 6. Data Schema Dependencies

### 6.1 Primary Schemas

The system operates on a small number of primary schemas that define the data contracts between agents. The ApplicantCreditProfile schema is the foundational data structure produced by the Data Synthesizer and consumed by the Risk Engine and Advisory Agent. This schema is documented in detail in the architectural specification and includes all credit-related information about an applicant.

The RiskAssessment schema is produced by the Risk Engine and consumed by the Advisory Agent and Compliance Guardrail. This schema includes the risk score, probability of default, loss given default, risk tier, key factors, and model metadata.

The AdvisoryReport schema is produced by the Advisory Agent and consumed by the Journey Coach and Compliance Guardrail. This schema includes decision explanations, recommendations, product suggestions, and required disclosures.

The ComplianceValidation schema is produced by the Compliance Guardrail for all validated outputs. This schema includes validation status, issues identified, required modifications, and audit trail references.

### 6.2 Schema Evolution

Schemas evolve as requirements change, but schema changes require careful coordination to maintain backward compatibility. The following practices ensure schema stability. All schema changes are documented in the data dictionary (a separate artifact). Changes that add optional fields are backward compatible and can be deployed immediately. Changes that add required fields require coordinated deployment across all affected agents. Breaking changes require version bumps and migration planning.

The orchestration layer enforces schema validation at agent boundaries, rejecting messages that do not conform to expected schemas. This enforcement prevents integration issues caused by malformed data.

---

## 7. Appendix: Territory and Currency Reference

### 7.1 Supported Territories

The system supports all ECCU member territories as defined by the Eastern Caribbean Central Bank. The territory codes used in the system follow ISO 3166-1 alpha-2 standard. Antigua and Barbuda (AG), Dominica (DM), Grenada (GD), Montserrat (MS), Saint Kitts and Nevis (KN), Saint Lucia (LC), and Saint Vincent and the Grenadines (VC) are the primary territories served.

Each territory has specific configuration for credit bureau connectivity, currency, and regulatory requirements. The territory configuration is maintained in a centralized configuration store and referenced by all agents.

### 7.2 Currency Handling

All monetary amounts in the system are stored in Eastern Caribbean Dollars (XCD) with ISO 4217 currency code 951. The system handles automatic conversion from other currencies (USD, JMD, TTD) based on daily exchange rates published by the ECCB. Conversion rates are cached and refreshed daily.

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | February 2026 | Lead AI Architect | Initial version |

**Cross-References**

- Master Plan Checklist: Section 0.1
- Architectural Proposal v4: Section 2 (Complete Architecture)
- Work Breakdown Structure: ONT-002
- Data Dictionary: ONT-003
