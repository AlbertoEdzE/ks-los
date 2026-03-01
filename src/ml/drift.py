import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset
import os
from src.ml.train import generate_training_data

def run_drift_check(output_path: str = "doc/04_documentation/phase_4/drift_report.html"):
    ref = generate_training_data(n_samples=1000)
    # Ensure inference log exists
    if not os.path.exists("data/inference_log.csv"):
        raise FileNotFoundError("No inference log found at data/inference_log.csv")
    cur = pd.read_csv(
        "data/inference_log.csv",
        header=None,
        names=[
            "credit_score",
            "utilization_ratio",
            "total_debt",
            "history_length_months",
            "derogatory_marks",
            "thin_file_flag",
            "ml_prob_good",
            "ml_score",
            "decision"
        ]
    )
    # Align columns for comparison (subset of FEATURES)
    ref_subset = ref[[
        "credit_score",
        "utilization_ratio",
        "total_debt",
        "history_length_months",
        "derogatory_marks",
        "thin_file_flag"
    ]]
    cur_subset = cur[[
        "credit_score",
        "utilization_ratio",
        "total_debt",
        "history_length_months",
        "derogatory_marks",
        "thin_file_flag"
    ]]
    report = Report(metrics=[DataDriftPreset()])
    result = report.run(reference_data=ref_subset, current_data=cur_subset)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    result.save_html(output_path)
    return output_path

if __name__ == "__main__":
    print(run_drift_check())
