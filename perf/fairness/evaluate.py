import random
import statistics
from typing import List, Dict
from src.agents.data_synthesizer.scdg import SCDG
from src.ml.inference import CreditRiskModel
from src.shared.types import ApplicantCreditProfile

def sample_profiles(n: int) -> List[ApplicantCreditProfile]:
    gen = SCDG(seed="fairness")
    profiles: List[ApplicantCreditProfile] = []
    for _ in range(n):
        age = random.randint(20, 60)
        scenario = random.choice(["THIN_FILE_YOUNG", "PRIME_ESTABLISHED", "NEAR_PRIME"])
        profiles.append(gen.generate_profile({"age": age, "territory": "AG", "scenario_type": scenario}))
    return profiles

def approve(score: float) -> bool:
    return score >= 0.5

def evaluate(n: int = 50) -> Dict:
    model = CreditRiskModel()
    profiles = sample_profiles(n)
    groups = {"thin": [], "non_thin": []}
    for ap in profiles:
        flag = 1 if ap.summary.thin_file else 0
        s = model.predict(ap)["score"]
        (groups["thin"] if flag else groups["non_thin"]).append(s)
    thin_mean = statistics.mean(groups["thin"]) if groups["thin"] else 0.0
    non_thin_mean = statistics.mean(groups["non_thin"]) if groups["non_thin"] else 0.0
    thin_approval = sum(1 for s in groups["thin"] if approve(s)) / max(1, len(groups["thin"]))
    non_thin_approval = sum(1 for s in groups["non_thin"] if approve(s)) / max(1, len(groups["non_thin"]))
    return {
        "thin_mean": thin_mean,
        "non_thin_mean": non_thin_mean,
        "thin_approval": thin_approval,
        "non_thin_approval": non_thin_approval,
        "approval_gap": abs(thin_approval - non_thin_approval)
    }

if __name__ == "__main__":
    metrics = evaluate(100)
    print(metrics)
