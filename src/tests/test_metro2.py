import pytest
from datetime import date
from src.core.metro2 import Metro2Generator
from src.agents.data_synthesizer.scdg import SCDG
from src.shared.types import ApplicantCreditProfile

def test_metro2_segment_length():
    """Test that all generated segments are exactly 426 characters long."""
    scdg = SCDG(seed="metro2_test")
    profile = scdg.generate_profile({"age": 30, "territory": "AG"})
    
    generator = Metro2Generator()
    file_content = generator.generate_file(profile)
    
    lines = file_content.split("\n")
    for line in lines:
        assert len(line) == 426

def test_metro2_numeric_fields():
    """Test that numeric fields are correctly padded."""
    generator = Metro2Generator()
    assert generator._format_amount(100.0) == "000000100"
    assert generator._format_amount(0.0) == "000000000"
    assert generator._format_amount(12345.67) == "000012345" # Int conversion per simplified spec

def test_metro2_date_fields():
    """Test date formatting."""
    generator = Metro2Generator()
    d = date(2023, 12, 31)
    assert generator._format_date(d) == "12312023"
    assert generator._format_date(None) == "        "

def test_header_structure():
    """Test header record structure."""
    generator = Metro2Generator()
    header = generator._generate_header()
    assert header.startswith("HEADER")
    assert len(header) == 426

def test_trailer_structure():
    """Test trailer record structure."""
    generator = Metro2Generator()
    trailer = generator._generate_trailer(5)
    assert trailer.startswith("TRAILER")
    assert "000000005" in trailer
    assert len(trailer) == 426
