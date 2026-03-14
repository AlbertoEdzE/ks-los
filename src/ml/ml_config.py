import os
import sys
import tempfile
import uuid

# MLOps Configuration
# Local SQLite backend for simplicity and portability (Scientific Rigor: Reproducibility)
if "pytest" in sys.modules:
    _mlflow_db = os.path.join(tempfile.gettempdir(), f"ks_los_mlflow_{uuid.uuid4().hex}.db")
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", f"sqlite:///{_mlflow_db}")
else:
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
EXPERIMENT_NAME = "credit_risk_model_v2"

# Model Parameters
MODEL_ARTIFACT_PATH = "xgboost_model"
REGISTERED_MODEL_NAME = "CreditRiskScorer"

# Feature Engineering
FEATURES = [
    "age",
    "credit_score",
    "utilization_ratio",
    "total_debt",
    "history_length_months",
    "derogatory_marks",
    "thin_file_flag"
]

TARGET = "is_good_credit"
