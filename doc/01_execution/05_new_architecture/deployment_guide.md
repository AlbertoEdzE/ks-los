# Deployment Guide: ML Model Integration

## Prerequisites
- **Frontend**: Node.js 18+ (Vite)
- **Backend**: Python 3.10+, FastAPI
- **MLflow**: Running instance or configured remote tracking URI.
- **Docker**: Optional, for containerized deployment.

## Deployment Steps

### 1. Environment Setup
Ensure the following environment variables are set:
- `MLFLOW_TRACKING_URI`: URL to your MLflow server (e.g., `http://localhost:5000` or S3 bucket path).
- `ENV`: Deployment environment (`dev`, `staging`, `production`).
- `OTLP_URL`: Optional, for OpenTelemetry tracing.

### 2. Backend Deployment
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Start Server**:
   ```bash
   uvicorn src.main:app --host 0.0.0.0 --port 8000
   ```
   For production, use gunicorn with uvicorn workers:
   ```bash
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.main:app
   ```

### 3. Frontend Deployment
1. **Build**:
   ```bash
   cd frontend
   npm run build
   ```
   This generates static files in `frontend/dist`.
2. **Serve**:
   Serve the `dist` folder using Nginx, Apache, or a static site host (e.g., S3 + CloudFront).
   Ensure `vite.config.ts` is configured to proxy API requests to the backend URL if running separately.

### 4. Verification
1. Access the Admin Panel (e.g., `http://localhost:5173`).
2. Login with Admin credentials.
3. Navigate to the **ML Training** tab.
4. Verify the "Planning", "Execution", and "Deployment" steps are visible.
5. Check `/health` endpoint on the backend.

### Troubleshooting
- **Frontend can't connect to Backend**: Check CORS settings in `src/main.py`. Ensure `allow_origins` includes your frontend domain.
- **MLflow Model Load Failure**: Verify `MLFLOW_TRACKING_URI` is reachable and the model `credit_risk_model` is registered in the correct stage (`Production`).
- **Drift Report 404**: Ensure the report file path is writable by the backend process.
