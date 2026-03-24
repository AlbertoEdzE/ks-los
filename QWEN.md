# KS LOS - AI-Driven Agentic Loan Prequalification System

## Project Overview

**KS LOS** is a Caribbean-focused, privacy-preserving, agentic loan prequalification and financial advisory system. It follows a "Sovereign Core" philosophy with a fully local, open-source foundation that can evolve into a connected ecosystem.

**Current Phase:** Phase 3 (Advanced Decisioning & Compliance)

### Core Technologies

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI, Python 3.11, LangGraph |
| **Frontend** | React 19, TypeScript, Vite, TailwindCSS |
| **Database** | PostgreSQL (with pgvector), Redis |
| **AI/LLM** | Local Ollama (Qwen 2.5 7B, Nomic Embed Text) |
| **ML Ops** | MLflow, Evidently (drift detection) |
| **Observability** | Prometheus, Grafana, Jaeger, OpenTelemetry |
| **Compliance** | Metro 2 File Generation (Base Segment) |

### Architecture Components

- **Agent Core**: LangGraph-based multi-agent system with workflow orchestration
- **Decisioning**: RAG-based Risk Engine using PGVector and Ollama
- **SCDG**: Synthetic Credit Data Generator for development and fallback scenarios
- **Knowledge Base**: Vector store for Credit Policies
- **Frontend**: React Chat Interface connected to Agent API

---

## Building and Running

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js & npm/pnpm
- **Ollama** installed locally and running (`ollama serve`)
- Required Ollama models:
  ```bash
  ollama pull qwen2.5:7b
  ollama pull nomic-embed-text
  ```

### Quick Start (Recommended)

Start the full development stack (API, observability, frontend):

```bash
bash scripts/launch_dev.sh
```

**Stack URLs:**
| Service | URL |
|---------|-----|
| API | http://localhost:8000/health |
| Metrics | http://localhost:8000/metrics |
| Observability Summary | http://localhost:8000/observability/summary |
| MLflow | http://localhost:5000/ |
| Prometheus | http://localhost:9090/ |
| Grafana | http://localhost:3000/ |
| Drift Report | http://localhost:8000/training/drift/report |
| Frontend | http://localhost:5174/ |

### Stop Development Stack

```bash
bash scripts/stop_dev.sh
```

### Manual Setup

#### 1. Infrastructure (PostgreSQL, Redis, Observability)

```bash
make up
```

Check infrastructure health:
```bash
make check-infra
```

#### 2. Knowledge Base Initialization

```bash
source venv/bin/activate
python scripts/init_kb.py
```

#### 3. Backend Server

```bash
python -m src.main
# or
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Swagger docs: http://localhost:8000/docs

#### 4. Frontend Development Server

```bash
cd frontend
npm install  # or pnpm install
npm run dev
```

### Docker Images

GitHub Actions builds and publishes:
- API: `ghcr.io/<owner>/ks-los-api:latest`
- Frontend: `ghcr.io/<owner>/ks-los-frontend:latest`

---

## Development

### Testing

Run backend tests with coverage:

```bash
pytest --cov=src src/tests/
```

Run integration tests (requires infrastructure):

```bash
RUN_INTEGRATION=1 pytest src/tests/
```

The project maintains >90% code coverage.

### Test Structure

| Directory | Purpose |
|-----------|---------|
| `src/tests/` | Backend unit tests |
| `tests/integration/` | Integration tests |
| `e2e/` | End-to-end Playwright tests |

### Key Makefile Commands

| Command | Description |
|---------|-------------|
| `make up` | Start Docker infrastructure |
| `make down` | Stop Docker infrastructure |
| `make logs` | Tail Docker logs |
| `make test` | Run tests |
| `make db-reset` | Reset database (drop volumes) |
| `make check-infra` | Verify infrastructure health |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_JSON` | Enable JSON logging | `1` |
| `OTLP_URL` | OpenTelemetry collector URL | `http://localhost:4317` |
| `MLFLOW_TRACKING_URI` | MLflow server URI | `http://localhost:5000` |
| `ENFORCE_RBAC` | Enable role-based access control | `0` |
| `ENV` | Environment (local/prod) | `local` |
| `CORS_ALLOW_ORIGINS` | Allowed CORS origins | Auto (localhost) |
| `RUN_INTEGRATION` | Run integration tests | `0` |

### Correlation IDs

Send `X-Correlation-ID` header in requests to correlate logs, traces, and MLflow runs:

```bash
curl -H "X-Correlation-ID: test-123" http://localhost:8000/health
```

---

## Project Structure

```
ks-los/
├── src/
│   ├── agents/           # LangGraph agents, nodes, tools, prompts
│   ├── api/
│   │   └── routers/      # FastAPI route handlers (17 routers)
│   ├── config/           # Configuration modules
│   ├── core/             # Core business logic (Metro 2, Knowledge Base)
│   ├── ml/               # ML scripts (train, inference, drift)
│   ├── shared/           # Shared utilities (auth, db, logging, metrics)
│   └── tests/            # Unit tests
├── frontend/             # React + TypeScript application
├── infrastructure/
│   ├── docker-compose.yml
│   └── observability/    # Prometheus, Grafana, OTEL configs
├── doc/
│   ├── 00_planning/      # Project plans
│   ├── 01_execution/     # Execution documentation
│   ├── 02_Loan-Navigator-AI/
│   └── 02_v2/            # V2 API documentation
├── scripts/              # Helper scripts (launch, clean, init)
├── e2e/                  # Playwright end-to-end tests
├── perf/                 # Performance and fairness evaluation
├── mlruns/               # MLflow artifacts (git-ignored)
└── test-results/         # Test output artifacts
```

### Key Source Directories

| Directory | Contents |
|-----------|----------|
| `src/agents/` | Agent workflow graph, nodes (journey_coach, risk_engine, advisory), tools, state management |
| `src/api/routers/` | API endpoints: agent, scdg, training, metrics, observability, explain, admin, v2_* |
| `src/core/` | Metro 2 compliance, Knowledge Base with RAG |
| `src/ml/` | Model training, inference, drift detection with Evidently |
| `src/shared/` | Cross-cutting concerns: auth, audit, correlation, logging, metrics |

---

## Development Conventions

### Coding Style

- **Python**: Follows PEP 8, uses type hints (Pydantic v2 for validation)
- **TypeScript**: Strict mode enabled, ESLint configured
- **Logging**: Structured JSON logging (configurable via `LOG_JSON`)

### Architecture Patterns

- **Agent Workflow**: LangGraph state machine with conditional edges
- **API Design**: RESTful routers grouped by domain (admin, v2, support)
- **Observability**: OpenTelemetry tracing with correlation ID propagation
- **Security**: RBAC enforcement in production, CORS restrictions

### Git & Contribution

- Integration tests marked with `@pytest.mark.integration` (skipped by default)
- Production requires `ENFORCE_RBAC=1` and `API_KEYS` configured
- Docker images published via GitHub Actions to GHCR

---

## Troubleshooting

### Common Issues

1. **Ollama not reachable**: Ensure `ollama serve` is running locally
2. **Port conflicts**: `launch_dev.sh` automatically frees ports before starting
3. **Import errors**: Activate virtual environment and reinstall dependencies
4. **Database connection**: Run `make up` to start PostgreSQL/Redis containers

### Log Files

| File | Location |
|------|----------|
| Backend logs | `backend.log` |
| Frontend logs | `frontend.log` |
| Process PIDs | `.pid_api`, `.pid_frontend` |

---

## License

Private / Proprietary
