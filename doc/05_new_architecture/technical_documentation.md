# Technical Documentation: ML Model Integration System

## Overview
This document details the architectural changes implemented to support the new ML Model Training integration system. The system has been restructured to provide a comprehensive admin interface for managing the machine learning lifecycle, from synthetic data generation to model deployment.

## Architecture

### Frontend Architecture
The frontend has been refactored from a tab-based single component (`AdminPanel.tsx`) into a modular component-based architecture using a vertical sidebar for navigation.

**Key Components:**
- **Sidebar (`frontend/src/components/Sidebar.tsx`)**: Manages navigation state and renders the collapsible vertical menu.
- **AdminPanel (`frontend/src/components/AdminPanel.tsx`)**: The main container that orchestrates the layout and renders active components based on sidebar selection.
- **TrainingPanel (`frontend/src/components/TrainingPanel.tsx`)**: A new dedicated component for the ML training workflow (Planning -> Execution -> Deployment).
- **SyntheticDataControl (`frontend/src/components/SyntheticDataControl.tsx`)**: Extracted component for data generation.
- **ModelPanel (`frontend/src/components/ModelPanel.tsx`)**: Extracted component for model inference testing and explainability.
- **ConfigurationPanel** & **MetricsPanel**: Extracted components for system configuration and monitoring.

### Backend Architecture
The backend (FastAPI) has been extended to support the new training and model management workflows.

**New & Updated Routers:**
- **Training Router (`src/api/routers/training_router.py`)**: Handles training plan generation, execution, and drift detection.
- **Model Management Router (`src/api/routers/model_manage_router.py`)**: A new router for administrative model operations, specifically hot-reloading the model in production.
- **Inference Engine (`src/ml/inference.py`)**: Updated to support dynamic model reloading from MLflow without service restart.

### Data Flow
1. **Training Initiation**: Admin requests a training plan -> Backend generates hyperparameters/strategy.
2. **Execution**: Admin approves plan -> Backend triggers training job -> Model logged to MLflow.
3. **Deployment**: Admin clicks deploy -> Backend `reload_model` endpoint called -> `CreditRiskModel` singleton re-fetches latest Production model from MLflow.

## Technologies Used
- **Frontend**: React, TypeScript, Vite
- **Backend**: FastAPI, Python 3.10+
- **ML Ops**: MLflow (Model Registry), XGBoost (Model), Evidently (Drift Detection)
- **Testing**: Playwright (E2E), Pytest (Unit/Integration)

## Security
- **Role-Based Access Control (RBAC)**: All sensitive endpoints (`/training/*`, `/model/reload`) require `operator` or `admin` roles.
- **Audit Logging**: All critical actions (training execution, model deployment) are logged via `src.shared.audit`.
