# Project Review

## Overview
This document serves as a comprehensive review of the project, capturing detailed information about the structure, components, and overall purpose of the system. It will be updated regularly to reflect new insights and changes.

## Directory Structure

### Root Directory
- **Dockerfile**: Configuration for building Docker images.
- **Makefile**: Contains build, test, and deployment scripts.
- **README.md**: Documentation for the project.
- **conftest.py**: Configuration for pytest.
- **test_xgb_error.py**: A test script related to XGBoost errors.

### doc
- **02_Loan-Navigator-AI/.local/skills/canvas/__init__.py**: Initialization file for a specific skill.
- **review.md**: This document.

### e2e
- End-to-end tests for the application.

### frontend
- Frontend code (likely in React, Vue, Angular, etc.).

### image
- Directory for Docker images or other image-related files.

### infrastructure
- Infrastructure-as-code (IaC) files, likely using tools like Terraform, CloudFormation, or Kubernetes manifests.

### mlflow.db
- Database file used by MLflow for tracking experiments and models.

### mlruns
- Directory containing MLflow run data.

### model.log
- Log file for model training or other processes.

### perf
- Performance-related scripts, including `fairness/evaluate.py`.

### requirements.txt
- List of Python dependencies.

### scripts
- Various scripts for initialization and maintenance tasks, such as `init_kb.py`.

### src
- The main source code directory, containing the core logic of the application.
  - **agents**: Contains modules for data synthesis, workflow graph, nodes, prompts, state management, tools, and tests.
  - **api**: API routers handling different endpoints.
  - **config**: Configuration files.
  - **core**: Core components of the system.
  - **ml**: Machine learning scripts for model training, inference, drift detection, and configuration.
  - **shared**: Shared utilities and types.
  - **tests**: Unit and integration tests for the application.

### test-results
- Directory for storing test results.

### tests
- Unit and integration tests for the application.

## Core Components

### Agents
The `src/agents` directory contains several submodules:
- **data_synthesizer**: Generates synthetic credit profiles based on predefined archetypes.
- **graph.py**: Defines the workflow graph for the agents.
- **nodes.py**: Implements specific steps in the workflow.
- **prompts.py**: Provides system prompts to guide agent behavior during interactions.
- **state.py**: Manages the state of the agent workflow.
- **tools.py**: Contains utility functions and classes for tasks like training models and generating synthetic data.
- **tests/test_training_agent.py**: Unit tests for the `training_agent` module.
- **training_agent.py**: Implements the training agent for the credit risk model.

### API Routers
The `src/api` directory contains multiple API routers:
- **__init__.py**: Initialization file.
- **admin_config_router.py**: Handles admin configuration endpoints.
- **admin_seed_router.py**: Handles admin seed endpoints.
- **admin_synthetic_router.py**: Handles admin synthetic data endpoints.
- **agent_router.py**: Handles agent-related endpoints.
- **chat_support_router.py**: Handles chat support endpoints.
- **explain_router.py**: Handles explainability endpoints.
- **metrics_router.py**: Handles metrics endpoints.
- **model_manage_router.py**: Handles model management endpoints.
- **observability_router.py**: Handles observability endpoints.
- **scdg_router.py**: Handles synthetic credit data generation (SCDG) endpoints.
- **training_router.py**: Handles training-related endpoints.
- **v2_auth.py**: Handles v2 authentication endpoints.
- **v2_catalog_products_router.py**: Handles v2 catalog products endpoints.
- **v2_conversations_router.py**: Handles v2 conversations endpoints.
- **v2_loans_router.py**: Handles v2 loans endpoints.
- **v2_phases_router.py**: Handles v2 phases endpoints.

### Machine Learning
The `src/ml` directory contains scripts for:
- **__init__.py**: Initialization file.
- **drift.py**: Handles drift detection.
- **inference.py**: Handles model inference.
- **ml_config.py**: Configuration for machine learning components.
- **train.py**: Scripts for training models.
- **training_manager.py**: Manages the training process.

### Shared Utilities
The `src/shared` directory contains shared utilities and types:
- **audit.py**: Audit-related utilities.
- **auth.py**: Authentication utilities.
- **correlation.py**: Correlation analysis utilities.
- **db.py**: Database utilities.
- **logging.py**: Logging utilities.
- **metrics.py**: Metrics collection utilities.
- **types.py**: Shared data types and structures.

### Tests
The `src/tests` directory contains unit and integration tests:
- **__init__.py**: Initialization file.
- **test_admin_config_router.py**: Tests for the admin configuration router.
- **test_admin_seed_router.py**: Tests for the admin seed router.
- **test_admin_synthetic_router.py**: Tests for the admin synthetic data router.
- **test_api.py**: General API tests.
- **test_chat_support_router.py**: Tests for the chat support router.
- **test_drift_api.py**: Tests for drift detection endpoints.
- **test_explain_inference_api.py**: Tests for explainability and inference endpoints.
- **test_graph.py**: Tests for the workflow graph.
- **test_knowledge_base.py**: Tests for the knowledge base.
- **test_knowledge_base_integration.py**: Integration tests for the knowledge base.
- **test_metrics_and_observability.py**: Tests for metrics and observability.
- **test_metrics_exposure_after_generation.py**: Tests for metrics exposure after generation.
- **test_metro2.py**: Tests for Metro 2 validation.
- **test_metro2_compliance.py**: Compliance tests for Metro 2.
- **test_ml_integration.py**: Integration tests for machine learning components.
- **test_rbac_api.py**: Tests for role-based access control (RBAC) endpoints.
- **test_risk_engine_logic.py**: Tests for risk engine logic.
- **test_scdg.py**: Tests for synthetic credit data generation (SCDG).
- **test_synthetic_data_integration.py**: Integration tests for synthetic data generation.
- **test_tools.py**: Tests for utility tools.
- **test_training_agent_api.py**: Tests for the training agent API.
- **test_v2_product_api.py**: Tests for v2 product endpoints.
- **test_wp_v2_019_observability.py**: Observability tests for a specific workflow (WP V2.019).

## System Overview
The project is a loan origination system designed for Caribbean territories. It includes components for synthetic data generation, risk assessment, and financial advisory services. The system is built to handle the entire process from applicant interaction to credit decision-making.

### Key Components
- **Data Synthesizer**: Generates synthetic credit profiles for testing and development.
- **Workflow Graph**: Defines the flow of operations, ensuring a structured and consistent process.
- **Nodes**: Implement specific steps in the workflow, such as generating profiles, assessing risk, and providing advisory recommendations.
- **Prompts**: Provide system prompts to guide agent behavior during interactions.
- **State Management**: Manages the state of the agent workflow, storing relevant information at each step.
- **Machine Learning**: Includes scripts for training models, making inferences, and detecting drift.
- **API Routers**: Expose various endpoints for different features and services.
- **Frontend**: A web application built using a modern JavaScript framework (React, Vue, Angular).

### Goals and Philosophy
The primary goal of the project is to provide a reliable and efficient loan origination system for Caribbean territories. The system aims to streamline the credit application process, ensure compliance with regulations, and provide accurate risk assessments.

The philosophy behind the project includes:
- **Modularity**: The system is designed as a collection of modular components, each responsible for a specific aspect of the process.
- **Automation**: Automating repetitive tasks to reduce manual effort and improve accuracy.
- **Data-Driven Decision Making**: Leveraging synthetic data and machine learning to make informed decisions.
- **Security and Compliance**: Ensuring that all processes adhere to regulatory requirements and maintain high standards of security.

## Next Steps
- [ ] Continue exploring the project and updating this document with more detailed information.
- [ ] Document any new insights or changes as they are discovered.
- [ ] Ensure comprehensive coverage of all components and their interactions.
