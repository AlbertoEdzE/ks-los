try:
    import mlflow
except Exception:
    mlflow = None
import pandas as pd
import logging
import os
from typing import Dict, Optional, Any

from src.shared.types import ApplicantCreditProfile
from src.ml.ml_config import (
    MLFLOW_TRACKING_URI, REGISTERED_MODEL_NAME, FEATURES
)

logger = logging.getLogger(__name__)

class CreditRiskModel:
    _instance = None
    _model = None
    _current_version = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CreditRiskModel, cls).__new__(cls)
            cls._instance._load_model()
        return cls._instance

    def _load_model(self, version: Optional[str] = None):
        """
        Loads the latest production model from MLflow, or a specific version.
        """
        try:
            if mlflow is None:
                logger.warning("MLflow is not available; skipping model load.")
                self._model = None
                return False
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            from mlflow.tracking import MlflowClient
            client = MlflowClient()
            
            if version:
                target_version = version
            else:
                # Get latest version dynamically
                versions = client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
                if not versions:
                    logger.warning(f"No registered models found for {REGISTERED_MODEL_NAME}")
                    self._model = None
                    return False
                # Sort by version number
                target_version = sorted(versions, key=lambda x: int(x.version))[-1].version
            
            model_uri = f"models:/{REGISTERED_MODEL_NAME}/{target_version}"
            logger.info(f"Loading model from {model_uri}...")
            self._model = mlflow.xgboost.load_model(model_uri)
            self._current_version = target_version
            logger.info(f"Model version {target_version} loaded successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def reload_model(self):
        """Reloads the latest model."""
        return self._load_model()

    def get_version(self):
        return self._current_version

    def list_versions(self):
        try:
            if mlflow is None:
                return []
            from mlflow.tracking import MlflowClient
            client = MlflowClient()
            versions = client.search_model_versions(f"name='{REGISTERED_MODEL_NAME}'")
            return sorted([
                {"version": v.version, "stage": v.current_stage, "run_id": v.run_id, "timestamp": v.creation_timestamp}
                for v in versions
            ], key=lambda x: int(x["version"]), reverse=True)
        except Exception:
            return []
    def rollback(self):
        """Rolls back to the previous version relative to the current one."""
        if not self._current_version:
            return False, "No model currently loaded"
        
        versions = self.list_versions()
        if not versions:
            return False, "No versions found"
            
        # Find index of current version
        try:
            current_idx = next(i for i, v in enumerate(versions) if v["version"] == self._current_version)
            if current_idx + 1 < len(versions):
                prev_version = versions[current_idx + 1]["version"]
                success = self._load_model(version=prev_version)
                return success, f"Rolled back to version {prev_version}" if success else "Failed to load previous version"
            else:
                return False, "No previous version available"
        except StopIteration:
            # Current version not in list (maybe deleted?), try loading latest-1
            if len(versions) > 1:
                 prev_version = versions[1]["version"]
                 success = self._load_model(version=prev_version)
                 return success, f"Current version unknown, loaded second latest {prev_version}"
            return False, "Cannot determine rollback target"

    def predict(self, profile: ApplicantCreditProfile | Dict[str, Any]) -> Dict[str, float]:
        """
        Predicts credit risk for a profile or a feature dictionary.
        Returns: {"probability_good": float, "score": float}
        """
        if not self._model:
            logger.warning("Model not loaded. Returning default neutral score.")
            return {"probability_good": 0.5, "score": 0.5}

        try:
            if isinstance(profile, dict):
                # Assume profile is a dict of features
                features = profile
                # If features are missing, fill with defaults or fail?
                # Let's assume frontend sends complete feature set or partial.
            else:
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
            
            # Ensure column order matches training, if columns are missing, add them as 0
            for col in FEATURES:
                if col not in df.columns:
                    df[col] = 0
            
            df = df[FEATURES]
            
            prob = self._model.predict_proba(df)[0][1] # Probability of Class 1 (Good)
            
            return {
                "probability_good": float(prob),
                "score": float(prob) # XGBoost prob IS the score in this context
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return {"probability_good": 0.5, "score": 0.5}
