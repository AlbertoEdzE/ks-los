# Phase 3: Advanced Decisioning & Compliance

## Status: Completed

## Overview
Phase 3 focuses on enhancing the "Brain" of the system. While Phase 2 established the agentic workflow and data generation, Phase 3 implements the actual credit decisioning logic using a Retrieval-Augmented Generation (RAG) approach and ensures regulatory compliance through Metro 2 reporting.

## Objectives
1.  **Scientific Decisioning**: Replace the rule-based risk engine with a RAG-based system that queries a "Credit Policy" document to make decisions.
2.  **Regulatory Compliance**: Implement a rigorous Metro 2 file generator to convert synthetic profiles into the standard industry format (Base Segment + J1/J2 Segments).
3.  **Knowledge Base**: Establish a `KnowledgeBase` class using `PGVector` and `nomic-embed-text` to store and retrieve policy documents.

## Architecture Changes

### 1. Knowledge Base (RAG)
-   **Embedding Model**: `nomic-embed-text` (Local via Ollama).
-   **Vector Store**: `PGVector` (PostgreSQL extension).
-   **Document Store**: Markdown-based policy documents in `doc/policies`.
-   **Integration**: The `Risk Engine` node will query the KB for "Credit Policy for [Territory]" before asking the LLM to evaluate the profile.

### 2. Risk Engine 2.0
-   **Input**: `ApplicantCreditProfile`.
-   **Process**:
    1.  Extract `territory` and `credit_score` from profile.
    2.  Retrieve relevant policy sections (e.g., "Minimum Score", "DTI Limits").
    3.  Construct a prompt with:
        -   Profile Summary
        -   Retrieved Policy Rules
        -   Decision Instructions
    4.  LLM generates a `RiskDecision` (Approved/Declined/Manual) with `reasoning`.

### 3. Metro 2 Generator
-   **Class**: `Metro2Generator`.
-   **Function**: `generate_metro2_string(profile: ApplicantCreditProfile) -> str`.
-   **Standards**: Follows CDIA Metro 2 Format (426-character fixed-width string).
    -   **Header Segment**: Identifier for the data provider.
    -   **Base Segment**: Primary consumer data.
    -   **J1/J2 Segments**: Address/Employment data (optional but good for rigor).
    -   **Trailer Segment**: Totals.

## Implementation Steps
1.  **Dependencies**: Add `langchain-postgres` and `psycopg`. (Done)
2.  **Metro 2**: Implement `src/core/metro2.py`. (Done)
3.  **Knowledge Base**: Implement `src/core/knowledge_base.py`. (Done)
4.  **Policy**: Create `doc/policies/credit_policy_v1.md`. (Done)
5.  **Agent Update**: Modify `risk_engine_node` in `src/agents/nodes.py`. (Done)
6.  **Testing**: Unit tests for Metro 2 compliance and RAG retrieval. (Done)

## Validation Criteria
-   **Metro 2**: Output string must be exactly 426 characters (or multiple thereof for blocked records) and pass regex validation for numeric/alphanumeric fields. (Validated)
-   **RAG**: Querying "minimum score" must retrieve the correct section from the policy document. (Validated)
-   **Decision**: A "THIN_FILE_YOUNG" profile should trigger a specific policy rule (e.g., "Refer for manual review" or "Decline" depending on policy). (Validated)
