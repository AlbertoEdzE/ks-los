# Phase 4 Plan: Predictive Analytics & MLOps

## 1. Overview
Building on the "Brain" (Phase 3 Risk Engine), Phase 4 focuses on **Continuous Learning and Optimization**. We will transition from a static rule/RAG-based system to a dynamic, data-driven ecosystem using **MLOps principles**. This aligns with the "Scientific Rigor" directive by enabling reproducible experiments, model tracking, and champion/challenger validation.

## 2. Objectives
1.  **MLOps Infrastructure**: Fully integrate **MLflow** for experiment tracking, model registry, and artifact storage.
2.  **Predictive Modeling**: Train the first **XGBoost Credit Scoring Model** using the synthetic portfolio generated in Phase 1/2.
3.  **Continuous Improvement**: Implement a "Champion/Challenger" framework where the RAG-based decisioning (Champion) is compared against the XGBoost model (Challenger) or vice-versa.
4.  **Scientific Validation**: Automate the generation of "Validation Reports" using **Evidently AI** to detect data drift and model performance degradation.

## 3. Work Breakdown Structure (WBS)

### 4.1 MLOps Setup (Week 1)
- [x] **4.1.1** Configure MLflow Tracking Server (Local) with SQLite backend.
    - *Status*: Implemented in `src/ml/ml_config.py` using `mlflow.db`.
- [ ] **4.1.2** Instrument `RiskEngine` to log all decisions (inputs, outputs, latency) to MLflow.
    - *Note*: Currently logging via standard Python logging. Need to add MLflow inference logging.
- [x] **4.1.3** Create a `ModelRegistry` abstraction to load models dynamically.
    - *Status*: Implemented `CreditRiskModel` singleton in `src/ml/inference.py`.

### 4.2 Model Training Pipeline (Week 2)
- [x] **4.2.1** Create `src/ml/train.py`: A reproducible training script that:
    - Loads data from SCDG.
    - Preprocesses features (One-Hot Encoding, Scaling).
    - Trains XGBoost Classifier.
    - Logs metrics (AUC, Gini, Precision/Recall) to MLflow.
    - *Status*: Completed.
- [x] **4.2.2** Define Feature Store schema (Input variables for the model).
    - *Status*: Defined in `train.py` (numerical/categorical features).
- [ ] **4.2.3** Implement "Thin File" specific model tuning (Hyperopt).

### 4.3 Evaluation & Drift Detection (Week 3)
- [ ] **4.3.1** Integrate **Evidently AI** for data drift detection.
- [ ] **4.3.2** Create a daily job to compare "Recent Traffic" vs. "Training Data".
- [ ] **4.3.3** Generate automated HTML reports for the "Executive Terminal".

### 4.4 Agent Integration (Week 4)
- [x] **4.4.1** Update `risk_engine_node` to support **Ensemble Decisioning**:
    - **Logic**: If RAG Policy = "Manual Review" AND XGBoost Score > 700 -> "Approve (Low Confidence)".
    - *Status*: Implemented in `src/agents/nodes.py`.
- [ ] **4.4.2** Implement Feedback Loop: Allow "Manual Review" outcomes to be tagged as ground truth for retraining.

## 4. Deliverables
1.  **MLflow Dashboard**: Accessible locally, showing experiment history.
2.  **Trained Model Artifact**: A `.pkl` or `.json` XGBoost model versioned in MLflow.
3.  **Drift Report**: An automated report showing input distribution stability.
4.  **Updated Risk Engine**: Capable of using both Policy (RAG) and Probability (XGBoost).

## 5. Success Criteria
-   **Reproducibility**: `make train` produces the exact same model given the same seed.
-   **Traceability**: Every credit decision is linked to a specific model version and policy document version.
-   **Performance**: XGBoost model achieves > 0.75 AUC on synthetic holdout set.
-   **Safety**: Drift alerts trigger if input data deviates by > 10% (PSI).

## 6. Resource Requirements
-   **Compute**: Local CPU (XGBoost is efficient).
-   **Storage**: ~1GB for MLflow artifacts and SQLite DB.
-   **Data**: Existing 1,000+ record synthetic portfolio.
