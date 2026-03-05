# API Specifications: ML Model Management & Training

## Overview
This API specification describes the endpoints added for the ML model training lifecycle and management. All endpoints require `X-Correlation-ID` and JWT authentication (Admin/Operator role).

### Training Endpoints
Base Path: `/training`

#### 1. Generate Training Plan
- **POST** `/training/plan`
- **Description**: Proposes a training plan (hyperparameters, data sample size) based on rationale.
- **Request Body**:
  ```json
  {
    "rationale": "Periodic model refresh"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "plan": {
      "hyperparameters": { "learning_rate": 0.1, ... },
      "n_samples": 1000,
      "notes": "..."
    }
  }
  ```
- **Required Role**: `operator`

#### 2. Execute Training
- **POST** `/training/execute`
- **Description**: Executes the training job with the provided plan.
- **Request Body**:
  ```json
  {
    "hyperparameters": { ... },
    "n_samples": 1000,
    "notes": "..."
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "result": {
      "accuracy": 0.95,
      "auc": 0.98,
      "model_uri": "models:/credit_risk_model/1"
    }
  }
  ```
- **Required Role**: `operator`

#### 3. Run Drift Check
- **POST** `/training/drift`
- **Description**: Runs evidently data drift report generation.
- **Response (200 OK)**:
  ```json
  {
    "report_path": "doc/...",
    "report_endpoint": "/training/drift/report"
  }
  ```
- **Required Role**: `operator`

### Model Management Endpoints
Base Path: `/model`

#### 1. Reload Model
- **POST** `/model/reload`
- **Description**: Forces the inference service to reload the latest production model from MLflow.
- **Response (200 OK)**:
  ```json
  {
    "status": "reloaded",
    "message": "Model reloaded successfully from MLflow"
  }
  ```
- **Required Role**: `admin`

#### 2. Get Model Status
- **GET** `/model/status`
- **Description**: Checks if a model is currently loaded in memory.
- **Response (200 OK)**:
  ```json
  {
    "loaded": true,
    "type": "<class 'xgboost.core.Booster'>"
  }
  ```

## Error Handling
- **401 Unauthorized**: Missing or invalid token.
- **403 Forbidden**: Insufficient permissions (role check failed).
- **500 Internal Server Error**: Backend processing failure (e.g., MLflow connection error).
