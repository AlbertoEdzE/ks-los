# Work Breakdown Structure

**Document ID:** WBS-001
**Version:** 1.0
**Phase:** 0.2
**Status:** Draft
**Last Updated:** February 2026

---

## 1. Purpose and Scope

This document establishes the formal Work Breakdown Structure (WBS) for the AI-Driven Agentic System for Loan Prequalification and Financial Advisory. The WBS transforms the five-phase implementation timeline from the architectural proposal into a hierarchical decomposition of all work required to deliver the complete system. Each element in the WBS represents a discrete work package that can be independently estimated, assigned, executed, and validated.

The WBS follows the five-level decomposition model specified in the master plan. Level 1 represents the five major phases of the project. Level 2 breaks each phase into its constituent milestones. Level 3 identifies the specific deliverables produced at each milestone. Level 4 decomposes deliverables into individual technical tasks. Level 5 captures the test cases, documentation artifacts, and configuration items required to complete each technical task.

This WBS serves multiple critical functions in project management. It provides the foundation for effort estimation and scheduling, enabling accurate timeline projections and resource allocation. It creates the structure for work assignment, allowing individual packages to be delegated to agents or team members with clear ownership. It establishes the basis for progress tracking, providing measurable milestones that indicate project advancement. Finally, it enables risk management by making dependencies explicit and identifying critical path items that cannot be delayed without impacting the overall schedule.

---

## 2. WBS Overview

### 2.1 Level 1: Project Phases

The project is organized into six major phases, each representing a distinct stage of the delivery lifecycle. Phase 0 encompasses the foundation setup activities that must be completed before any implementation work begins. Phases 1 through 5 represent the progressive enhancement of system capabilities, with each phase building upon the foundation established by previous phases.

| Phase | Description | Duration | Cumulative Duration |
|-------|-------------|----------|---------------------|
| Phase 0 | Foundation Setup | 2 weeks | 2 weeks |
| Phase 1 | Open Core | 6 weeks | 8 weeks |
| Phase 2 | Predictive Enhancement | 6 weeks | 14 weeks |
| Phase 3 | External Data Integration | 8 weeks | 22 weeks |
| Phase 4 | Cloud LLM Option | 4 weeks | 26 weeks |
| Phase 5 | Full Ecosystem | Ongoing | 26+ weeks |

### 2.2 Phase 0: Foundation Setup

Phase 0 establishes all prerequisite infrastructure, configurations, and documentation required for successful implementation. This phase has no external deliverables but must be completed in full before Phase 1 begins. The phase includes four major work areas corresponding to sections 0.1 through 0.4 of the master plan.

The first work area is Project Ontology Definition, which creates the authoritative reference for all system components, agent boundaries, and integration points. The second work area is Work Breakdown Structure Development, which creates this document and all supporting estimation materials. The third work area is Version Control Configuration, which establishes the repository, branching strategy, and branch protection rules. The fourth work area is Issue Tracking Setup, which configures the JIRA project, ticket templates, and automation rules.

Phase 0 completion criteria require that all four work areas are fully documented, reviewed, and approved. No implementation work may begin until Phase 0 is complete.

### 2.3 Phase 1: Open Core

Phase 1 delivers a fully functional loan prequalification system operating entirely on synthetic credit data. At phase completion, the system processes end-to-end workflows without any external dependencies beyond the development environment. This phase includes seven major milestones that deliver the core system capabilities.

The first milestone is MCP Infrastructure and SCDG Schema, which establishes the message coordination platform and defines the core credit data schemas. The second milestone is SCDG Implementation, which delivers the synthetic credit data generator with eight profile archetypes. The third milestone is Document Processing Pipeline, which enables bank statement upload and parsing. The fourth milestone is Data Synthesizer Agent, which orchestrates all data acquisition and normalization. The fifth milestone is Risk Engine and Model, which delivers the XGBoost-based scoring system. The sixth milestone is Advisory and Compliance Agents, which provide recommendation generation and regulatory validation. The seventh milestone is Journey Coach and UI, which delivers the applicant-facing interface and executive terminal.

---

## 3. Level 2: Phase Milestones

### 3.1 Phase 0 Milestones

#### 0.1 Project Ontology Definition

This milestone produces the complete system taxonomy document. The deliverable is the Project Ontology Definition artifact (ONT-001) as created in section 0.1. The milestone is complete when the ontology is reviewed by all stakeholders and approved as the authoritative reference. No technical tasks are associated with this milestone beyond documentation review and approval.

#### 0.2 Work Breakdown Structure

This milestone produces the formal WBS document. The deliverable is this document (WBS-001). The milestone is complete when all work packages are defined with estimates and dependencies. The acceptance criterion is that every item in the implementation timeline has a corresponding WBS entry with effort estimate and dependency mapping.

#### 0.3 Version Control Configuration

This milestone establishes the complete version control infrastructure. The deliverables include the Git repository with proper directory structure, the branching strategy documentation, branch protection rules configured in the Git hosting platform, and agent-specific branch prefixes enabled. The milestone is complete when all developers can clone the repository, create branches, and submit pull requests following the defined workflow.

#### 0.4 Issue Tracking Setup

This milestone establishes the complete issue tracking infrastructure. The deliverables include the JIRA project with appropriate issue types, custom fields configured, ticket templates for each work package type, automation rules for status updates, and priority matrix defined. The milestone is complete when all WBS work packages are represented as JIRA tickets with appropriate assignments and dependencies.

### 3.2 Phase 1 Milestones

#### 1.1 MCP Infrastructure and SCDG Schema (Weeks 1-2)

The MCP (Message Coordination Platform) infrastructure provides the communication backbone for all agent interactions. This milestone delivers the message broker configuration, schema validation infrastructure, and initial SCDG data specifications.

The milestone deliverables include the message broker (Redis streams) configured and tested, the ApplicantCreditProfile JSON schema defined and validated, the Metro 2 field mapping documentation completed, and the Moov-IO Metro 2 Docker container running locally with validation tests passing. The completion criterion is that all unit tests pass against the validator and the schema is fully documented.

This milestone has a single critical dependency: Phase 0 completion. The milestone cannot start until all Phase 0 work is complete.

#### 1.2 SCDG Implementation (Weeks 3-4)

The Synthetic Credit Data Generator is the cornerstone of Phase 1 development. This milestone delivers the complete SCDG capable of producing statistically realistic Caribbean credit profiles that pass Metro 2 validation.

The milestone deliverables include eight archetype parameter tables with Caribbean-calibrated distributions, the Markov chain payment history generator implemented and tested, the deterministic seeding mechanism for reproducible test data, integration with the Credit Bureau Source Adapter pattern, and a 1,000-record synthetic portfolio for initial model training. The completion criterion is that 100% of generated records pass Metro 2 validation and the generator produces statistically plausible profiles for all eight archetypes.

The critical path dependency for this milestone is milestone 1.1 completion. The SCDG implementation cannot begin until the schema and validation infrastructure are in place.

#### 1.3 Document Processing Pipeline (Weeks 3-4)

The document processing pipeline enables applicants to upload bank statements in PDF and CSV formats. This milestone delivers the complete extraction and normalization capability.

The milestone deliverables include the Docling integration for PDF bank statement extraction, CSV parsing for spreadsheet statement uploads, data normalization to internal transaction schema, and error handling for malformed documents. The completion criterion is that the pipeline successfully extracts transaction data from at least five major Caribbean bank statement formats.

This milestone runs in parallel with milestone 1.2. Both can proceed once milestone 1.1 is complete.

#### 1.4 Data Synthesizer Agent (Weeks 5-6)

The Data Synthesizer Agent orchestrates all data acquisition and normalization. This milestone delivers the complete agent with all source adapters integrated.

The milestone deliverables include the Credit Bureau Source Adapter with live/synthetic routing logic, the Bank Statement Adapter integrated with the processing pipeline, the Internal Bank Adapter for CRM and deposit history, the complete data normalization layer, and unit and integration tests for all components. The completion criterion is that the agent produces valid ApplicantCreditProfile documents from all supported data sources.

The critical path dependency for this milestone is completion of milestones 1.1, 1.2, and 1.3. The Data Synthesizer cannot be built until its data sources are defined and implemented.

#### 1.5 Risk Engine and Model (Weeks 5-6)

The Risk Engine delivers the XGBoost-based credit scoring capability. This milestone includes the complete model training and inference infrastructure.

The milestone deliverables include the feature engineering pipeline extracting 200+ derived features from credit profiles, the base XGBoost model trained on the 1,000-record synthetic portfolio, SHAP explanation generation for individual assessments, the model registry for version management, and the inference API with sub-second response time. The completion criterion is that the model produces valid risk scores for all valid input profiles with appropriate confidence intervals.

This milestone runs in parallel with milestone 1.4. Both depend on the data sources but can proceed independently once those sources are available.

#### 1.6 Advisory and Compliance Agents (Week 7)

The Advisory Agent generates personalized recommendations while the Compliance Guardrail validates regulatory adherence. This milestone delivers both agents.

The milestone deliverables include the Advisory Agent with RAG-powered recommendation generation using local Ollama LLM, the Compliance Guardrail with fair lending and disclosure validation rules, the rules engine with declarative compliance rule definition, and the audit logging infrastructure for regulatory compliance. The completion criterion is that both agents produce valid outputs for all test scenarios.

The critical path dependency for this milestone is completion of milestone 1.5. The Advisory Agent requires risk assessments as input, and the Compliance Guardrail validates Advisory outputs.

#### 1.7 Journey Coach and UI (Week 8)

The Journey Coach Agent and user interfaces complete the system. This milestone delivers the complete applicant-facing and loan officer-facing applications.

The milestone deliverables include the Journey Coach Agent with complete conversation workflow management, the Applicant Chat UI with responsive design, the Executive Terminal for loan officer review and approval, and end-to-end integration tests validating complete workflows. The completion criterion is that a complete prequalification workflow can be executed from applicant registration through loan officer decision.

The critical path dependency for this milestone is completion of all previous Phase 1 milestones. The Journey Coach integrates all other agents and cannot be completed until those agents are operational.

---

## 4. Level 3: Deliverables

### 4.1 Deliverables Mapping

The following table maps each milestone to its specific deliverables with associated effort estimates in story points.

| Milestone | Deliverable | Story Points | Dependencies |
|-----------|-------------|--------------|--------------|
| 1.1 | Message broker configuration | 5 | 0.4 |
| 1.1 | ApplicantCreditProfile schema | 8 | 0.4 |
| 1.1 | Metro 2 mapping documentation | 5 | 0.1 |
| 1.1 | Moov-IO validator Docker setup | 3 | 0.4 |
| 1.2 | Eight archetype parameter tables | 13 | 1.1 |
| 1.2 | Markov chain generator | 21 | 1.1 |
| 1.2 | Deterministic seeding | 8 | 1.2 |
| 1.2 | Source Adapter integration | 8 | 1.1, 1.2 |
| 1.2 | Synthetic portfolio (1K records) | 5 | 1.2 |
| 1.3 | Docling PDF extraction | 13 | 1.1 |
| 1.3 | CSV parsing | 8 | 1.1 |
| 1.3 | Data normalization | 8 | 1.1, 1.3 |
| 1.3 | Error handling | 5 | 1.3 |
| 1.4 | Credit Bureau Source Adapter | 13 | 1.1, 1.2 |
| 1.4 | Bank Statement Adapter | 8 | 1.3, 1.4 |
| 1.4 | Internal Bank Adapter | 8 | 1.4 |
| 1.4 | Normalization layer | 8 | 1.4 |
| 1.4 | Agent unit and integration tests | 13 | 1.4 |
| 1.5 | Feature engineering pipeline | 21 | 1.1, 1.2 |
| 1.5 | XGBoost model training | 13 | 1.5 |
| 1.5 | SHAP explanations | 8 | 1.5 |
| 1.5 | Model registry | 5 | 1.5 |
| 1.5 | Inference API | 8 | 1.5 |
| 1.6 | Advisory Agent with RAG | 21 | 1.4, 1.5 |
| 1.6 | Compliance Guardrail rules | 13 | 1.6 |
| 1.6 | Audit logging | 8 | 1.6 |
| 1.7 | Journey Coach Agent | 21 | 1.4, 1.5, 1.6 |
| 1.7 | Applicant Chat UI | 34 | 1.7 |
| 1.7 | Executive Terminal | 21 | 1.7 |
| 1.7 | E2E integration tests | 13 | 1.7 |

### 4.2 Story Points Summary

The total effort for Phase 1 implementation is 323 story points. Based on a team capacity of 40 story points per week (assuming two developers working at 20 points each), the phase requires approximately 8.1 weeks. This aligns with the planned 6-week duration by assuming some parallelization and initial velocity gains.

The highest-effort deliverables are the Applicant Chat UI (34 points), Feature Engineering Pipeline (21 points), Markov Chain Generator (21 points), Journey Coach Agent (21 points), Advisory Agent with RAG (21 points), and Docling PDF Extraction (13 points). These items represent the critical path and should be assigned to the most experienced developers or agents.

---

## 5. Level 4: Technical Tasks

### 5.1 SCDG Implementation Tasks

The SCDG Implementation milestone decomposes into the following technical task categories.

#### 5.1.1 Archetype Parameter Tables

This task category delivers the statistical parameters that define eight credit profile archetypes. Each archetype represents a distinct segment of the Caribbean credit population with characteristic score distributions, account types, and payment behaviors.

The eight archetypes are Thin File Young (age 18-25, no credit history), Thin File Immigrant (established adult, new to Caribbean), Prime Established (long history, good payment record), Near Prime (some late payments, stable), Recovering (past bad, now improving), Stressed (current delinquencies), High Utilization (maxed cards, making payments), and Defaulted (charge-offs or collections).

Technical tasks within this category include researching Caribbean credit market statistics to calibrate parameters, implementing parameter tables in JSON format with distribution definitions, creating validation scripts to verify parameter plausibility, and documenting archetype selection logic. Each archetype requires approximately 1.5 story points of effort, for a total of 13 story points.

#### 5.1.2 Markov Chain Generator

This task category implements the payment history generation logic using Markov chain modeling. The generator produces 24-month payment history strings that realistically model transitions between payment statuses.

Technical tasks within this category include designing state space (on-time, 30 days late, 60 days late, 90+ days late, no payment, no history), implementing transition probability matrices for each archetype, coding the generation algorithm with proper seeding, adding seasonality coefficients to reflect Caribbean economic cycles, and unit testing state transitions against expected distributions. This category requires 21 story points.

### 5.2 Risk Engine Tasks

#### 5.2.1 Feature Engineering Pipeline

This task category implements the complete feature extraction from raw credit profiles to model-ready feature vectors. The pipeline produces over 200 derived features organized into categories.

Technical tasks within this category include implementing utilization ratio features (current balance, credit limit, monthly payment ratios), implementing payment behavior features (on-time percentages, late payment counts, worst status ever), implementing credit depth features (oldest account, newest account, average age), implementing inquiry features (recent inquiries, inquiry frequency), implementing derived features (debt-to-income proxies, payment-to-income ratios), and implementing feature normalization and missing value handling. This category requires 21 story points.

---

## 6. Level 5: Test Cases and Artifacts

### 6.1 Test Case Framework

Each technical task produces associated test cases organized by testing level. Unit tests validate individual functions and classes in isolation. Integration tests validate interactions between components. End-to-end tests validate complete workflows.

For the SCDG, test cases validate Markov chain transition probabilities, parameter table completeness, validation gate rejection of invalid records, deterministic seeding reproducibility, and statistical plausibility of generated profiles. Test coverage must exceed 90% for this component.

For the Risk Engine, test cases validate feature extraction accuracy, model inference correctness, SHAP explanation consistency, inference latency requirements, and model version handling. Test coverage must exceed 90% for this component.

### 6.2 Documentation Artifacts

Each milestone produces associated documentation. Architecture documents describe system design decisions and rationale. API documentation describes all external interfaces. Runbooks describe operational procedures for deployment and maintenance. User guides describe functionality for end users.

---

## 7. Dependencies and Critical Path

### 7.1 Dependency Analysis

Dependencies between work packages follow two patterns. Finish-to-start dependencies represent technical constraints where one package cannot begin until another completes. Resource dependencies represent shared resources that limit parallel execution.

The critical path for Phase 1 runs through the SCDG implementation. Any delay to SCDG delays the Data Synthesizer, which delays the Risk Engine, which delays the Advisory Agent, which delays the Journey Coach. The total float on this path is zero.

Secondary paths through document processing and the UI have more float but still represent significant schedule risk.

### 7.2 Risk Mitigation

To mitigate critical path risk, the SCDG implementation should begin immediately upon Phase 1 start with the most experienced resources. Parallel work on document processing should begin as soon as milestone 1.1 completes, even while SCDG work continues. The UI development can begin with mock integrations while agents are being built.

---

## 8. Phase 2-5 Summary

### 8.1 Phase 2: Predictive Enhancement (Weeks 9-14)

Phase 2 delivers enhanced predictive capabilities including a specialized thin-file model for applicants without credit bureau history and production ML infrastructure for ongoing model improvement.

| Milestone | Description | Deliverables |
|-----------|-------------|--------------|
| 2.1 | Thin-File Model | Separate XGBoost model for zero-history applicants |
| 2.2 | ML Infrastructure | MLflow integration, model versioning, performance monitoring |
| 2.3 | Champion/Challenger | A/B routing between model variants |

### 8.2 Phase 3: External Data Integration (Weeks 15-22)

Phase 3 delivers live credit bureau connectivity for territories where EveryData ECCU is operational.

| Milestone | Description | Deliverables |
|-----------|-------------|--------------|
| 3.1 | EveryData Integration | Live API connection for Antigua, Grenada, St Lucia |
| 3.2 | Additional Bureaus | CCBL and CreditInfo JM integration |
| 3.3 | Employment Verification | NIS and remittance income adapters |

### 8.3 Phase 4: Cloud LLM Option (Weeks 23-26)

Phase 4 enables cloud LLM backends for the Advisory Agent when API keys are configured.

| Milestone | Description | Deliverables |
|-----------|-------------|--------------|
| 4.1 | Cloud Routing | Automatic routing between local and cloud LLM |
| 4.2 | A/B Evaluation | Comparison framework for local vs. cloud quality |

### 8.4 Phase 5: Full Ecosystem (Month 7+)

Phase 5 delivers additional channels and capabilities for full ecosystem operation.

| Milestone | Description | Deliverables |
|-----------|-------------|--------------|
| 5.1 | Additional Channels | WhatsApp and SMS integration |
| 5.2 | DCash Integration | CBDC transaction signals |
| 5.3 | Multi-Territory | Configuration management for all territories |
| 5.4 | Regulatory Reporting | Automated ECCB compliance reports |

---

## 9. Appendix: Effort Estimation Reference

### 9.1 Story Points Guide

The following reference guides effort estimation for common task types. Complex tasks (new algorithm implementation, unknown technology) are estimated at 13-21 points. Moderate tasks (feature addition, integration work) are estimated at 5-8 points. Simple tasks (configuration, documentation) are estimated at 1-3 points.

### 9.2 Velocity Assumptions

Initial team velocity is assumed to be 30-40 story points per week. Velocity is expected to increase to 40-50 points per week after the first phase as the team gains familiarity with the codebase and tooling.

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | February 2026 | Lead AI Architect | Initial version |

**Cross-References**

- Master Plan Checklist: Section 0.2
- Project Ontology Definition: ONT-001
- Data Dictionary: ONT-003 (future)
- Issue Tracking Setup: ONT-004 (future)
