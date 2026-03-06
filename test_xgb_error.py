
import xgboost as xgb
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

def test_xgb():
    params = {
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "learning_rate": 0.1,
        "max_depth": 5,
        "n_estimators": 100
    }

    X = np.random.rand(100, 5)
    y = np.random.randint(0, 2, 100)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    class ProgressCallback(xgb.callback.TrainingCallback):
        def after_iteration(self, model, epoch, evals_log):
            print(f"Epoch {epoch}")
            return False

    try:
        clf = xgb.XGBClassifier(**params, callbacks=[ProgressCallback()])
        clf.fit(X_train, y_train)
        print("Fit successful")
        
        y_pred = clf.predict(X_test)
        print("Predict successful")
        
        # Check inheritance
        from sklearn.base import BaseEstimator, ClassifierMixin
        print(f"Is instance of BaseEstimator: {isinstance(clf, BaseEstimator)}")
        print(f"Is instance of ClassifierMixin: {isinstance(clf, ClassifierMixin)}")
        
        # Check explicit attribute
        if hasattr(clf, "_estimator_type"):
            print(f"_estimator_type: {clf._estimator_type}")
        else:
            print("_estimator_type is missing")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_xgb()
