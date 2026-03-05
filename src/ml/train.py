import pandas as pd
import numpy as np
import xgboost as xgb
import mlflow
import mlflow.xgboost
import logging
import os
import time
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score, f1_score, confusion_matrix
from datetime import date

from src.agents.data_synthesizer.scdg import SCDG
from src.ml.ml_config import (
    MLFLOW_TRACKING_URI, EXPERIMENT_NAME, 
    FEATURES, TARGET, REGISTERED_MODEL_NAME
)
from src.shared.correlation import get_correlation_id
from src.ml.training_manager import training_manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_training_data(n_samples: int = 1000, progress_callback=None) -> pd.DataFrame:
    """
    Generates synthetic training data using SCDG.
    """
    logger.info(f"Generating {n_samples} synthetic profiles...")
    if progress_callback:
        progress_callback(10, "generating_data", f"Starting generation of {n_samples} samples...")

    scdg = SCDG(seed="training_seed_v1")
    
    data = []
    
    # Archetype distribution for diversity
    archetypes = [
        ("THIN_FILE_YOUNG", 20, 0.1),
        ("PRIME_ESTABLISHED", 40, 0.3),
        ("NEAR_PRIME", 35, 0.2),
        ("STRESSED", 30, 0.2),
        ("DEFAULTED", 40, 0.2)
    ]
    
    # Normalize weights
    total_weight = sum(w for _, _, w in archetypes)
    probs = [w/total_weight for _, _, w in archetypes]
    
    batch_size = max(1, n_samples // 10) # Update progress every 10%

    for i in range(n_samples):
        # Pick random archetype based on weights
        idx = np.random.choice(len(archetypes), p=probs)
        arch_name, age, _ = archetypes[idx]
        
        # Add some variance to age
        age_var = np.random.randint(-5, 10)
        final_age = max(18, age + age_var)
        
        input_data = {
            "age": final_age,
            "territory": "AG",
            "scenario_type": arch_name
        }
        
        profile = scdg.generate_profile(input_data)
        
        # Flatten Profile to Features
        row = {
            "age": final_age,
            "credit_score": profile.summary.credit_score,
            "utilization_ratio": profile.summary.utilization_ratio,
            "total_debt": profile.summary.total_current_balance_xcd,
            "history_length_months": profile.summary.months_oldest_account,
            "derogatory_marks": profile.summary.derogatory_marks,
            "thin_file_flag": 1 if profile.summary.thin_file else 0,
            # Target Logic: 
            # 1 (Good) if no major derogatory marks and decent payment history
            # This logic mimics the "Ground Truth" we are trying to learn
            TARGET: 1 if (
                profile.summary.derogatory_marks == 0 and 
                profile.payment_behavior.worst_payment_status_ever in ["OK", "Current"] and
                profile.summary.utilization_ratio < 1.0
            ) else 0
        }
        data.append(row)
        
        if progress_callback and (i + 1) % batch_size == 0:
            pct = 10 + int((i + 1) / n_samples * 40) # 10% to 50%
            progress_callback(pct, "generating_data", f"Generated {i + 1}/{n_samples} samples")
        
    return pd.DataFrame(data)

def train_model(params: dict | None = None, n_samples: int = 2000) -> dict:
    """
    Main training pipeline.
    """
    training_manager.start_training()
    try:
        # 1. Setup MLflow
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(EXPERIMENT_NAME)
        
        with mlflow.start_run() as run:
            cid = get_correlation_id()
            if cid:
                mlflow.set_tags({"correlation_id": cid})
            
            # 2. Data Generation
            df = generate_training_data(n_samples=n_samples, progress_callback=training_manager.update_progress)
            
            training_manager.update_progress(50, "preprocessing", "Splitting dataset...")
            
            X = df[FEATURES]
            y = df[TARGET]
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
            
            training_manager.update_progress(60, "training", f"Training XGBoost on {len(X_train)} samples...")

            # 3. Train
            if params is None:
                params = {
                    "objective": "binary:logistic",
                    "eval_metric": "logloss",
                    "learning_rate": 0.1,
                    "max_depth": 5,
                    "n_estimators": 100
                }
            
            # Use callback for training progress
            class ProgressCallback(xgb.callback.TrainingCallback):
                def after_iteration(self, model, epoch, evals_log):
                    pct = 60 + int((epoch + 1) / params.get("n_estimators", 100) * 30) # 60% to 90%
                    training_manager.update_progress(pct, "training", f"Epoch {epoch+1}/{params.get('n_estimators', 100)}")
                    return False

            clf = xgb.XGBClassifier(**params, callbacks=[ProgressCallback()])
            clf.fit(X_train, y_train)
            
            training_manager.update_progress(90, "evaluating", "Evaluating model...")

            # 4. Evaluate
            y_pred = clf.predict(X_test)
            y_prob = clf.predict_proba(X_test)[:, 1]
            
            acc = accuracy_score(y_test, y_pred)
            auc = roc_auc_score(y_test, y_prob)
            prec = precision_score(y_test, y_pred, zero_division=0)
            rec = recall_score(y_test, y_pred, zero_division=0)
            f1 = f1_score(y_test, y_pred, zero_division=0)
            cm = confusion_matrix(y_test, y_pred).tolist()

            # Log metrics
            mlflow.log_metrics({
                "accuracy": acc, 
                "auc": auc,
                "precision": prec,
                "recall": rec,
                "f1": f1
            })
            
            # Log model
            mlflow.xgboost.log_model(clf, "model", registered_model_name=REGISTERED_MODEL_NAME)
            
            result = {
                "accuracy": float(acc),
                "auc": float(auc),
                "precision": float(prec),
                "recall": float(rec),
                "f1": float(f1),
                "confusion_matrix": cm,
                "model_uri": f"runs:/{run.info.run_id}/model",
                "run_id": run.info.run_id,
                "dataset_size": n_samples,
                "train_size": len(X_train),
                "test_size": len(X_test)
            }
            
            training_manager.complete_training(result)
            return result
            
    except Exception as e:
        logger.error(f"Training failed: {e}")
        training_manager.fail_training(str(e))
        raise e

if __name__ == "__main__":
    train_model()
