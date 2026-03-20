# AI-Driven Agentic System for Loan Prequalification and Financial Advisory

## Overview
This project implements a Caribbean-focused, privacy-preserving, agentic loan prequalification and advisory system. It follows a "Sovereign Core" philosophy, starting with a fully local, open-source foundation (Phase 1) that can evolve into a connected ecosystem (Phase 2+).

**Current Status: Phase 3 (Advanced Decisioning & Compliance)**
-   **Agent Core**: Implemented using LangGraph.
-   **Decisioning**: RAG-based Risk Engine using `PGVector` and `Ollama`.
-   **Compliance**: Metro 2 File Generation (Base Segment).
-   **LLM**: Local Ollama (Qwen 2.5 7B, Nomic Embed Text).
-   **Frontend**: React Chat Interface connected to Agent API.

## Architecture
The system relies on a **Synthetic Credit Data Generator (SCDG)** for development and fallback scenarios. This generator produces Metro 2-compliant credit profiles based on Caribbean market archetypes.

### Key Components
- **Backend:** FastAPI, Python 3.11, LangGraph
- **Frontend:** React, TypeScript, Vite
- **Database:** PostgreSQL (with pgvector), Redis
- **AI/LLM:** Local Ollama (Qwen 2.5 7B, Nomic Embed Text)
- **Knowledge Base:** Vector store for Credit Policies.

## Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js & pnpm
- **Ollama** installed locally and running (`ollama serve`)
- **Models**:
  ```bash
  ollama pull qwen2.5:7b
  ollama pull nomic-embed-text
  ```

## Quick Start

### Observability & Dev Launch
To start API, observability stack (MLflow, Prometheus, Grafana), and frontend:
```bash
bash scripts/launch_dev.sh
```
Stack URLs:
- API: http://localhost:8000/health
- Metrics: http://localhost:8000/metrics
- Observability Summary: http://localhost:8000/observability/summary
- MLflow: http://localhost:5000/
- Prometheus: http://localhost:9090/
- Grafana: http://localhost:3000/
- Drift Report: http://localhost:8000/training/drift/report

Correlation IDs:
- Send `X-Correlation-ID` in requests to correlate logs, traces, and MLflow runs.
  Example: `curl -H "X-Correlation-ID: test-123" http://localhost:8000/health`

### Docker Images
GitHub Actions builds and publishes images:
- API: `ghcr.io/<owner>/ks-los-api:latest`
- Frontend: `ghcr.io/<owner>/ks-los-frontend:latest`
Use these in production deployments behind TLS reverse proxy and with proper environment configs.

### Stop Dev Stack
To stop API/frontend and observability stack:
```bash
bash scripts/stop_dev.sh
```

## Manual Setup

### 1. Infrastructure
Start Postgres and Redis:
```bash
make up
```
Check health (ensures Ollama is reachable):
```bash
make check-infra
```

### 2. Knowledge Base
Initialize the vector store:
```bash
source venv/bin/activate
python scripts/init_kb.py
```

### 3. Backend
Run the API server:
```bash
python -m src.main
```
Swagger docs: `http://localhost:8000/docs`.

### 4. Frontend
Navigate to frontend directory:
```bash
cd frontend
pnpm install
pnpm dev
```

## Testing
The project maintains >90% code coverage.

Run backend tests with coverage report:
```bash
pytest --cov=src src/tests/
```

## Directory Structure
- `src/agents`: Agent implementations (LangGraph, SCDG, Tools)
- `src/api`: FastAPI application and routers
- `src/core`: Core business logic (Metro 2, Knowledge Base)
- `src/shared`: Shared types and utilities
- `src/tests`: Backend unit and integration tests
- `infrastructure`: Docker Compose and config
- `frontend`: React application
- `doc`: Project documentation (Policies, Plans)
- `scripts`: Helper scripts for launching and cleaning

## License
Private / Proprietary

## Implementation Checklist
- [x] Borrower journey UX aligned to the premium design (welcome + quick prompts)
- [x] Documents upload flow wired to real backend (no UI-only placeholders)
- [x] OCR/PDF text extraction enabled for uploaded documents (server-side)
- [x] Documents saved and tracked in database (status, metadata, timestamps)
- [x] Required documents reduced to 2 (ID/Passport + Job Letter) for borrower flow
- [x] Progressive borrower flow (UI does not jump ahead before user can reply)
- [x] Loan creation gated by required borrower inputs to avoid premature steps
- [x] STP “Run Checks” made safe for multiple clicks (idempotent processing)
- [x] Offer/acceptance/disbursement cards wired via backend + chat metadata
- [x] Automated regression coverage via Playwright E2E and backend/frontend tests
- [ ] Production-grade authentication (real users, reset flows, MFA/SSO options)
- [ ] Centralized secrets + environment management across dev/stage/prod
- [ ] Formal database migrations and schema versioning
- [ ] Cloud object storage for documents (S3/GCS/Azure) + encryption + retention
- [ ] Document validation intelligence (classification, expiry, mismatch, fraud signals)
- [ ] Configurable underwriting/STP policy packs and exception routing
- [ ] Compliance-grade audit logging (document access, decisions, user actions)
- [ ] Operational monitoring with alerts on funnel drop-off and failure rates
- [ ] Security hardening (rate limits, upload scanning, OWASP review, WAF readiness)
- [ ] Deployment packaging for production (TLS, reverse proxy, rolling updates)

## AI System Diagram
```text
                ┌──────────────────────────────┐
                │ Frontend (Borrower/Officer)  │
                │ React UI                     │
                └───────────────┬──────────────┘
                                │ HTTP
                                v
┌──────────────────────────────────────────────────────────┐
│ FastAPI Backend (KS-LOS)                                 │
│                                                          │
│  A) Borrower Journey (v2)                                │
│   - Builds prompt + chat history                         │
│   - Calls local LLM (Ollama)                             │
│   - Grounds fields (amount/tenure/debts)                 │
│   - Writes messages + intent summary                     │
│                                                          │
│  B) Agentic Graph (LangGraph)                            │
│   journey_coach → (tool?) → profile_parser → risk_engine │
│   → advisory                                             │
│   - Tool calling (GenerateProfileTool)                   │
│   - RAG policy lookup + ML model scoring                 │
│                                                          │
│  C) Documents & STP                                      │
│   - Upload files → OCR/PDF extraction                    │
│   - Store metadata/status + run checks (idempotent)      │
└───────────────┬───────────────────────┬──────────────────┘
                │                       │
                │ SQL (operational DB)  │ Vector SQL (RAG)
                v                       v
     ┌───────────────────────┐   ┌─────────────────────────┐
     │ Postgres (or SQLite)  │   │ Postgres + PGVector      │
     │ Conversations/Messages │   │ Policy embeddings store  │
     │ Loans/Documents        │   └─────────────────────────┘
     └───────────┬───────────┘
                 │ files on disk
                 v
        ┌─────────────────────┐
        │ File Storage         │
        │ data/uploads/...     │
        └─────────────────────┘

(Optional, for model ops)
     ┌─────────────────────┐
     │ MLflow Tracking      │
     │ training + inference │
     └─────────────────────┘
```
