import pytest
from src.agents.data_synthesizer.scdg import SCDG
from src.shared.types import ApplicantCreditProfile

def test_scdg_generation_thin_file():
    seed = "test_thin_file"
    generator = SCDG(seed=seed)
    
    applicant_data = {
        "age": 22,
        "territory": "AG",
        "scenario_type": "THIN_FILE_YOUNG"
    }
    
    profile = generator.generate_profile(applicant_data)
    
    assert isinstance(profile, ApplicantCreditProfile)
    assert profile.metadata.source == "synthetic"
    assert profile.metadata.synthetic_archetype == "THIN_FILE_YOUNG"
    assert profile.summary.thin_file == True
    assert profile.identity.address.territory_code == "AG"
    
def test_scdg_generation_prime():
    seed = "test_prime"
    generator = SCDG(seed=seed)
    
    applicant_data = {
        "age": 40,
        "territory": "LC",
        "scenario_type": "PRIME_ESTABLISHED"
    }
    
    profile = generator.generate_profile(applicant_data)
    
    assert isinstance(profile, ApplicantCreditProfile)
    assert profile.metadata.synthetic_archetype == "PRIME_ESTABLISHED"
    assert profile.summary.credit_score >= 720
    assert len(profile.trade_lines) >= 3

def test_scdg_determinism():
    seed = "deterministic_check"
    gen1 = SCDG(seed=seed)
    gen2 = SCDG(seed=seed)
    
    data = {"age": 30, "territory": "GD"}
    
    p1 = gen1.generate_profile(data)
    p2 = gen2.generate_profile(data)
    
    assert p1.identity.full_name == p2.identity.full_name
    assert p1.summary.credit_score == p2.summary.credit_score
    assert len(p1.trade_lines) == len(p2.trade_lines)
