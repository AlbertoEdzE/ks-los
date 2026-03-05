import mlflow
import pandas as pd
import logging
import os
from typing import Dict, Optional

from src.shared.types import ApplicantCreditProfile
from src.ml.ml_config import (
    MLFLOW_TRACKING_URI, REGISTERED_MODEL_NAME, FEATURES
)

logger = logging.getLogger(__name__)

class CreditRiskModel:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CreditRiskModel, cls).__new__(cls)
            cls._instance._load_model()
        return cls._instance

    def _load_model(self):
        """
        Loads the latest production model from MLflow.
        """
        try:
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            
            # Get latest version dynamically
            from mlflow.tracking import MlflowClient
            client = MlflowClient()
            # Get all versions and pick the last one (highest version number)
            # In a real prod env, we would filter by stage="Production"
            versions = client.get_latest_versions(REGISTERED_MODEL_NAME, stages=["None", "Production", "Staging"])
            if not versions:
                logger.warning(f"No registered models found for {REGISTERED_MODEL_NAME}")
                self._model = None
                return False

            # Sort by version number just in case
            latest_version = sorted(versions, key=lambda x: int(x.version))[-1].version
            
            model_uri = f"models:/{REGISTERED_MODEL_NAME}/{latest_version}"
            logger.info(f"Loading model from {model_uri}...")
            self._model = mlflow.xgboost.load_model(model_uri)
            logger.info("Model loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to load MLflow model: {e}")
            self._model = None
            return False

    def reload_model(self) -> bool:
        """
        Force reloads the model from MLflow.
        Returns True if successful, False otherwise.
        """
        return self._load_model()


    def predict(self, profile: ApplicantCreditProfile) -> Dict[str, float]:
        """
        Predicts credit risk for a profile.
        Returns: {"probability_good": float, "score": float}
        """
        if not self._model:
            logger.warning("Model not loaded. Returning default neutral score.")
            return {"probability_good": 0.5, "score": 0.5}

        try:
            # Flatten profile to match training features
            features = {
                "age": 2024 - profile.identity.date_of_birth.year, # Approx
                "credit_score": profile.summary.credit_score,
                "utilization_ratio": profile.summary.utilization_ratio,
                "total_debt": profile.summary.total_current_balance_xcd,
                "history_length_months": profile.summary.months_oldest_account,
                "derogatory_marks": profile.summary.derogatory_marks,
                "thin_file_flag": 1 if profile.summary.thin_file else 0
            }
            
            df = pd.DataFrame([features])
            
            # Ensure column order matches training
            df = df[FEATURES]
            
            prob = self._model.predict_proba(df)[0][1] # Probability of Class 1 (Good)
            
            return {
                "probability_good": float(prob),
                "score": float(prob) # XGBoost prob IS the score in this context
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {"probability_good": 0.5, "score": 0.5}
