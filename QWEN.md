# KS-LOS: AI-Driven Agentic Loan Prequalification System

## Project Overview

**KS-LOS** is a Caribbean-focused, privacy-preserving, agentic loan prequalification and financial advisory system. It follows a "Sovereign Core" philosophy with a local-first, open-source foundation that can evolve into a connected ecosystem.

**Current Status:** Phase 3 (Advanced Decisioning & Compliance)

### Key Features
- **Agent Core:** LangGraph-based multi-agent system for borrower journey orchestration
- **Decisioning:** RAG-based Risk Engine using PGVector and Ollama (Qwen 2.5 7B)
- **Compliance:** Metro 2 File Generation (Base Segment)
- **Frontend:** React chat interface with real-time agent interaction
- **Synthetic Data:** SCDG (Synthetic Credit Data Generator) for development and fallback

### Architecture Components
| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.11, LangGraph |
| Frontend | React, TypeScript, Vite, TailwindCSS |
| Database | PostgreSQL (with pgvector), Redis |
| AI/LLM | Local Ollama (Qwen 2.5 7B, Nomic Embed Text) |
| Observability | MLflow, Prometheus, Grafana, Jaeger, OpenTelemetry |

## Building and Running

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js & npm/pnpm
- **Ollama** (local LLM runtime)
  ```bash
  brew install ollama  # macOS
  ollama pull qwen2.5:7b
  ollama pull nomic-embed-text
  ```

### Quick Start (Recommended)

Launch the full development stack (API, observability, frontend):
```bash
bash scripts/launch_dev.sh
```

**Access URLs:**
| Service | URL |
|---------|-----|
| API Health | http://localhost:8000/health |
| API Docs (Swagger) | http://localhost:8000/docs |
| Metrics | http://localhost:8000/metrics |
| Observability Summary | http://localhost:8000/observability/summary |
| MLflow | http://localhost:5000/ |
| Prometheus | http://localhost:9090/ |
| Grafana | http://localhost:3000/ (admin/admin) |
| Jaeger Tracing | http://localhost:16686/ |
| Frontend | http://localhost:5174/ |

**Correlation IDs:** Send `X-Correlation-ID` header to correlate logs, traces, and MLflow runs.

### Stop Development Stack
```bash
bash scripts/stop_dev.sh
```

### Manual Setup

#### 1. Infrastructure (PostgreSQL, Redis, Observability)
```bash
make up
make check-infra  # Verify Ollama connectivity
```

#### 2. Knowledge Base Initialization
```bash
source venv/bin/activate
python scripts/init_kb.py
```

#### 3. Backend API
```bash
source venv/bin/activate
pip install -r requirements.txt
python -m src.main
# Or: uvicorn src.main:app --reload --port 8000
```

#### 4. Frontend
```bash
cd frontend
npm install
npm run dev
```

### Docker Deployment

Build and run production images:
```bash
# Images are published via GitHub Actions
docker pull ghcr.io/<owner>/ks-los-api:latest
docker pull ghcr.io/<owner>/ks-los-frontend:latest
```

**Production Requirements:**
- TLS reverse proxy
- `CORS_ALLOW_ORIGINS` set (no localhost)
- `ENFORCE_RBAC=1`
- `API_KEYS` configured
- `ENABLE_HSTS=1`

## Testing

### Backend Tests
```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src src/tests/

# Run integration tests (requires infrastructure)
RUN_INTEGRATION=1 pytest -m integration
```

### Frontend Tests
```bash
cd frontend

# Unit tests
npm run test

# E2E tests (Playwright)
npm run test:e2e
npm run test:e2e:ui      # Interactive UI
npm run test:e2e:report   # Show report
```

### E2E Integration Tests
```bash
cd e2e
npm install
npx playwright test
```

## Development Conventions

### Code Style
- **Python:** PEP 8, type hints with Pydantic v2 models
- **TypeScript:** Strict mode, ESLint with React hooks rules
- **Formatting:** Consistent indentation, meaningful variable names

### Project Structure
```
ks-los/
├── src/
│   ├── agents/          # LangGraph agents, nodes, tools, prompts
│   ├── api/             # FastAPI routers, schemas, middleware
│   ├── config/          # Configuration (LLM, settings)
│   ├── core/            # Business logic (Metro 2, Knowledge Base)
│   ├── ml/              # ML models (XGBoost, training, drift detection)
│   ├── shared/          # Utilities (logging, correlation, metrics)
│   └── tests/           # Backend unit/integration tests
├── frontend/
│   └── src/
│       ├── api/         # API client
│       ├── components/  # React components
│       └── types/       # TypeScript types
├── infrastructure/
│   ├── docker-compose.yml
│   └── observability/   # Prometheus, Grafana, OTEL configs
├── scripts/             # DevOps scripts (launch, stop, init)
├── e2e/                 # Playwright end-to-end tests
├── doc/                 # Documentation, plans, policies
└── data/                # Local data (uploads, inference logs)
```

### Key Patterns
- **Correlation IDs:** All requests support `X-Correlation-ID` for tracing
- **JSON Logging:** Set `LOG_JSON=1` for structured logs
- **OpenTelemetry:** Distributed tracing via OTLP to Jaeger
- **Metrics:** Prometheus counters for requests, errors, latency
- **RBAC:** Role-based access control (disabled in dev via `ENFORCE_RBAC=0`)

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_JSON` | `1` | Enable JSON structured logging |
| `OTLP_URL` | `http://localhost:4317` | OpenTelemetry collector endpoint |
| `ENFORCE_RBAC` | `0` | Enable RBAC middleware |
| `MLFLOW_TRACKING_URI` | `http://localhost:5000` | MLflow server URL |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Local LLM model |
| `CORS_ALLOW_ORIGINS` | (localhost list) | Allowed CORS origins |
| `API_KEYS` | (empty) | Production API keys |

### Git Workflow
- Feature branches: `feature/<description>`
- Bug fixes: `fix/<description>`
- Commits follow conventional commit format
- PRs require passing tests and coverage >90%

## API Endpoints Summary

| Router | Path | Description |
|--------|------|-------------|
| `v2_conversations` | `/api/v2/conversations` | Conversation management |
| `v2_borrower` | `/api/v2/borrower` | Borrower journey endpoints |
| `v2_loans` | `/api/v2/loans` | Loan CRUD and processing |
| `v2_documents` | `/api/v2/documents` | Document upload and OCR |
| `v2_phases` | `/api/v2/phases` | Journey phase transitions |
| `scdg` | `/api/scdg` | Synthetic data generation |
| `agent` | `/api/agent` | Agent chat interface |
| `training` | `/api/training` | Model training and drift |
| `metrics` | `/api/metrics` | Prometheus metrics |
| `observability` | `/api/observability` | Observability summary |

## Troubleshooting

### Common Issues

**Port conflicts:**
```bash
# Scripts auto-detect and free ports, or use alternates:
BACKEND_PORT=8001 FRONTEND_PORT=5175 bash scripts/launch_dev.sh
```

**Ollama not responding:**
```bash
ollama serve  # Start daemon
ollama pull qwen2.5:7b
```

**Database reset:**
```bash
make db-reset  # Drops and recreates volumes
```

**Dependency issues:**
```bash
# Recreate venv
rm -rf venv && python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Implementation Roadmap

### Completed
- [x] Borrower journey UX with progressive flow
- [x] Document upload with OCR/PDF extraction
- [x] Database tracking for documents
- [x] STP "Run Checks" idempotent processing
- [x] Offer/acceptance/disbursement workflow
- [x] Automated E2E regression coverage

### In Progress / Planned
- [ ] Production authentication (MFA/SSO)
- [ ] Cloud object storage (S3/GCS)
- [ ] Document validation intelligence
- [ ] Configurable underwriting policy packs
- [ ] Compliance-grade audit logging
- [ ] Production deployment packaging
