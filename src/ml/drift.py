import pandas as pd
import os
from src.ml.train import generate_training_data

try:
    from evidently import Report
    from evidently.presets import DataDriftPreset
    EVIDENTLY_AVAILABLE = True
except ImportError:
    EVIDENTLY_AVAILABLE = False
    print("Warning: 'evidently' not installed. Drift checks disabled.")

def run_drift_check(output_path: str = "doc/04_documentation/phase_4/drift_report.html"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    if not EVIDENTLY_AVAILABLE:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><body><h1>Drift check skipped</h1><p>evidently is not installed.</p></body></html>")
        return output_path

    if not os.path.exists("data/inference_log.csv"):
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(
                "<!DOCTYPE html><html><body><h1>Drift report unavailable</h1>"
                "<p>No inference log found at data/inference_log.csv.</p></body></html>"
            )
        return output_path

    try:
        ref = generate_training_data(n_samples=1000)
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
                "decision",
            ],
        )
        ref_subset = ref[
            [
                "credit_score",
                "utilization_ratio",
                "total_debt",
                "history_length_months",
                "derogatory_marks",
                "thin_file_flag",
            ]
        ]
        cur_subset = cur[
            [
                "credit_score",
                "utilization_ratio",
                "total_debt",
                "history_length_months",
                "derogatory_marks",
                "thin_file_flag",
            ]
        ]
        report = Report(metrics=[DataDriftPreset()])
        result = report.run(reference_data=ref_subset, current_data=cur_subset)
        result.save_html(output_path)
        return output_path
    except Exception as e:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"<!DOCTYPE html><html><body><h1>Drift check failed</h1><pre>{e}</pre></body></html>")
        return output_path

if __name__ == "__main__":
    print(run_drift_check())
