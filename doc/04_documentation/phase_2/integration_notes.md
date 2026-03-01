# Phase 2 Integration Notes

## Architecture Overview
The Phase 2 system integrates the following components:

1.  **Frontend (React + Vite)**:
    -   Communicates with the Backend via REST API.
    -   Key Components: `ChatInterface` (manages chat state), `CreditProfileView` (displays structured data).
    -   State Management: React `useState` (simple for now).

2.  **Backend (FastAPI)**:
    -   Exposes endpoints: `/agent/chat` and `/health`.
    -   **Agent Runtime**: Uses `LangGraph` to manage the stateful interaction.
    -   **LLM Provider**: Connects to local Ollama via `langchain-ollama`.

3.  **Agent Core (LangGraph)**:
    -   **State**: `AgentState` (messages, credit_profile, risk_score, advice).
    -   **Nodes**:
        -   `journey_coach`: Main LLM node.
        -   `tools`: Executes `GenerateProfileTool`.
        -   `risk_engine`: Calculates risk (rule-based stub).
        -   `advisory`: Generates advice based on risk.
    -   **Edges**: Conditional edge from `journey_coach` to `tools` or `END`.

4.  **Data Layer**:
    -   **SCDG**: Generates data on-the-fly.
    -   **Persistence**: Currently in-memory (per request) or LangGraph checkpointer (if configured).

## Configuration
-   **LLM**: Configured in `src/config/llm.py`. Defaults to `qwen2.5:7b` via Ollama at `http://localhost:11434`.
-   **Environment**: `.env` file controls API URLs and other settings.

## Running the System
Use the master script:
```bash
./scripts/start_all.sh
```
This starts:
1.  Docker containers (Postgres, Redis).
2.  Backend API (port 8000).
3.  Frontend Dev Server (port 5173).

## Troubleshooting
-   **Ollama Connection**: Ensure Ollama is running (`ollama serve`).
-   **Model Missing**: Run `ollama pull qwen2.5:7b`.
-   **Port Conflicts**: Check if ports 8000 or 5173 are in use.
