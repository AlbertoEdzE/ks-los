# AI-Driven Agentic System for Loan Prequalification and Financial Advisory

## Overview
This project implements a Caribbean-focused, privacy-preserving, agentic loan prequalification and advisory system. It follows a "Sovereign Core" philosophy, starting with a fully local, open-source foundation (Phase 1) that can evolve into a connected ecosystem (Phase 2+).

## Architecture
The system relies on a **Synthetic Credit Data Generator (SCDG)** for development and fallback scenarios. This generator produces Metro 2-compliant credit profiles based on Caribbean market archetypes.

### Key Components
- **Backend:** FastAPI, Python 3.11
- **Frontend:** React, TypeScript, Vite
- **Database:** PostgreSQL (with pgvector), Redis
- **AI/LLM:** Ollama (Qwen 2.5), LangGraph
- **Validation:** Moov-IO Metro 2 Validator (Docker)

## Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js & pnpm

## Getting Started

### 1. Infrastructure Setup
Start the required services (Postgres, Redis, Ollama, Metro 2 Validator):
```bash
make up
```
Check infrastructure health:
```bash
make check-infra
```

### 2. Backend Setup
Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the API server:
```bash
python -m src.main
```
The API will be available at `http://localhost:8000`.
Swagger docs: `http://localhost:8000/docs`.

### 3. Frontend Setup
Navigate to frontend directory:
```bash
cd frontend
pnpm install
```

Run the development server:
```bash
pnpm dev
```
The UI will be available at `http://localhost:5173`.

## Testing
Run backend tests:
```bash
make test
```

Run frontend tests:
```bash
cd frontend
pnpm test
```

## Directory Structure
- `src/agents`: Agent implementations (SCDG, etc.)
- `src/api`: FastAPI application and routers
- `src/shared`: Shared types and utilities
- `src/tests`: Backend unit and integration tests
- `infrastructure`: Docker Compose and config
- `frontend`: React application
- `doc`: Project documentation

## Synthetic Data Generator (SCDG)
The SCDG is accessible via the API `/scdg/generate`. It uses a deterministic seed to generate realistic Caribbean credit profiles.
Archetypes include:
- `THIN_FILE_YOUNG`
- `PRIME_ESTABLISHED`
- `STRESSED`
- And more.

## License
Private / Proprietary
