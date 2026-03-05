
import pytest
from unittest.mock import patch, MagicMock
from src.agents.training_agent import propose_training_plan

def test_propose_training_plan_success():
    """Test that plan is generated correctly when LLM succeeds."""
    mock_llm = MagicMock()
    mock_llm.invoke.return_value.content = '```json\n{"hyperparameters": {"learning_rate": 0.05}, "n_samples": 1000, "notes": "AI generated"}\n```'
    
    with patch('src.agents.training_agent.get_llm', return_value=mock_llm):
        context = {"rationale": "test"}
        plan = propose_training_plan(context)
        
        assert plan["n_samples"] == 1000
        assert plan["hyperparameters"]["learning_rate"] == 0.05
        assert plan["notes"] == "AI generated"

def test_propose_training_plan_fallback():
    """Test that fallback plan is returned when LLM fails."""
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("LLM connection failed")
    
    with patch('src.agents.training_agent.get_llm', return_value=mock_llm):
        context = {"n_samples": 500}
        plan = propose_training_plan(context)
        
        assert plan["n_samples"] == 500
        assert "fallback logic" in plan["notes"]
        assert "hyperparameters" in plan
