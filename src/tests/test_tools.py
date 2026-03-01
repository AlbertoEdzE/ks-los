import pytest
import json
from src.agents.tools import GenerateProfileTool

def test_generate_profile_tool_initialization():
    """Test that the tool initializes correctly."""
    tool = GenerateProfileTool()
    assert tool.name == "generate_credit_profile"
    assert "Generates a synthetic credit profile" in tool.description
    assert tool.args_schema is not None

def test_generate_profile_tool_execution():
    """Test the tool execution with valid arguments."""
    tool = GenerateProfileTool()
    # Arguments: age: int, territory: str
    result_json = tool._run(age=30, territory="GD")
    
    assert isinstance(result_json, str)
    result = json.loads(result_json)
    
    # Check correct structure based on ApplicantCreditProfile
    assert "identity" in result
    assert "summary" in result
    assert "metadata" in result
    assert result["identity"]["full_name"] is not None
    assert result["summary"]["credit_score"] is not None

def test_generate_profile_tool_determinism():
    """
    Test determinism. 
    Note: The tool constructs seed from args: f"{age}-{territory}-{scenario_type}"
    So same args should produce same result, except for timestamp in metadata.
    """
    tool = GenerateProfileTool()
    result1_json = tool._run(age=25, territory="LC", scenario_type="THIN_FILE")
    result2_json = tool._run(age=25, territory="LC", scenario_type="THIN_FILE")
    
    result1 = json.loads(result1_json)
    result2 = json.loads(result2_json)
    
    # Remove timestamp for comparison
    if "metadata" in result1 and "query_timestamp" in result1["metadata"]:
        del result1["metadata"]["query_timestamp"]
    if "metadata" in result2 and "query_timestamp" in result2["metadata"]:
        del result2["metadata"]["query_timestamp"]
    
    # Compare the rest
    assert result1 == result2

def test_generate_profile_tool_schema():
    """Test the tool's input schema."""
    tool = GenerateProfileTool()
    # In Pydantic V2 / LangChain 0.1, args_schema is available on instance
    schema = tool.args_schema
    properties = schema.model_json_schema()["properties"]
    assert "age" in properties
    assert "territory" in properties
    assert properties["age"]["type"] == "integer"
    assert properties["territory"]["type"] == "string"
