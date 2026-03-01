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
