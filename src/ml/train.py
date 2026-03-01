import pandas as pd
import numpy as np
import xgboost as xgb
import mlflow
import mlflow.xgboost
import logging
import os
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, precision_score, recall_score
from datetime import date

from src.agents.data_synthesizer.scdg import SCDG
from src.ml.ml_config import (
    MLFLOW_TRACKING_URI, EXPERIMENT_NAME, 
    FEATURES, TARGET, REGISTERED_MODEL_NAME
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_training_data(n_samples: int = 1000) -> pd.DataFrame:
    """
    Generates synthetic training data using SCDG.
    """
    logger.info(f"Generating {n_samples} synthetic profiles...")
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
    
    for _ in range(n_samples):
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
        
    return pd.DataFrame(data)

def train_model():
    """
    Main training pipeline.
    """
    # 1. Setup MLflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    with mlflow.start_run():
        # 2. Data Generation
        df = generate_training_data(n_samples=2000)
        
        X = df[FEATURES]
        y = df[TARGET]
        
        # 3. Split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # 4. Train XGBoost
        logger.info("Training XGBoost model...")
        params = {
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "max_depth": 4,
            "learning_rate": 0.1,
            "n_estimators": 100
        }
        
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train)
        
        # 5. Evaluate
        preds = model.predict(X_test)
        probs = model.predict_proba(X_test)[:, 1]
        
        acc = accuracy_score(y_test, preds)
        auc = roc_auc_score(y_test, probs)
        prec = precision_score(y_test, preds)
        rec = recall_score(y_test, preds)
        
        logger.info(f"Metrics: Accuracy={acc:.4f}, AUC={auc:.4f}")
        
        # 6. Log to MLflow
        mlflow.log_params(params)
        mlflow.log_metrics({
            "accuracy": acc,
            "auc": auc,
            "precision": prec,
            "recall": rec
        })
        
        # Log Model
        mlflow.xgboost.log_model(
            model, 
            "model", 
            registered_model_name=REGISTERED_MODEL_NAME
        )
        
        logger.info("Training complete. Model logged to MLflow.")

if __name__ == "__main__":
    train_model()
