"""
Unit Tests for Structured Output Parser

Tests XML tag extraction, JSON normalization, and Pydantic validation.
"""

import pytest
from src.agents.structured_parser import (
    XMLTagParser,
    ParsedOutput,
    IntentAnalysis,
    LoanSnapshot,
    LoanRecommendation,
    LoanApplication,
    DocumentsChecklist,
    DocumentItem,
    PhaseUpdate,
    parse_llm_response,
    extract_intent,
    extract_loan_snapshot,
    extract_recommendations,
)


class TestIntentAnalysis:
    """Test IntentAnalysis model validation"""
    
    def test_valid_intent_analysis(self):
        """Test parsing valid intent analysis"""
        data = {
            "purpose": "home_purchase",
            "urgency": "high",
            "monthly_income": "$8,000",
            "loan_amount": "$400,000",
            "employment_type": "salaried",
            "seriousness_score": 75,
            "fit_score": 82,
        }
        intent = IntentAnalysis(**data)
        
        assert intent.purpose == "home_purchase"
        assert intent.urgency == "high"
        assert intent.monthly_income == "$8,000"
        assert intent.seriousness_score == 75
        assert intent.fit_score == 82
    
    def test_intent_with_scores_out_of_range(self):
        """Test validation rejects scores outside 0-100"""
        with pytest.raises(Exception):
            IntentAnalysis(
                purpose="home_purchase",
                seriousness_score=150  # Invalid: > 100
            )
        
        with pytest.raises(Exception):
            IntentAnalysis(
                purpose="home_purchase",
                fit_score=-10  # Invalid: < 0
            )
    
    def test_intent_with_extra_fields(self):
        """Test that extra fields are allowed (Config.extra = 'allow')"""
        data = {
            "purpose": "auto_loan",
            "custom_field": "custom_value",
            "another_field": 123,
        }
        intent = IntentAnalysis(**data)
        
        assert intent.purpose == "auto_loan"
        assert intent.custom_field == "custom_value"  # type: ignore
        assert intent.another_field == 123  # type: ignore
    
    def test_intent_all_optional_fields(self):
        """Test that all fields are optional"""
        intent = IntentAnalysis()
        
        assert intent.purpose is None
        assert intent.seriousness_score is None
        assert intent.fit_score is None


class TestLoanSnapshot:
    """Test LoanSnapshot model validation"""
    
    def test_valid_loan_snapshot(self):
        """Test parsing valid loan snapshot"""
        data = {
            "loan_type": "Home Loan",
            "loan_amount": "$400,000",
            "estimated_em": "$2,800/month",
            "tenure": "20 years",
            "rate_band": "7.5% - 9.5%",
            "ltv": "85%",
            "currency": "$",
        }
        snapshot = LoanSnapshot(**data)
        
        assert snapshot.loan_type == "Home Loan"
        assert snapshot.loan_amount == "$400,000"
        assert snapshot.estimated_em == "$2,800/month"
        assert snapshot.ltv == "85%"
    
    def test_loan_snapshot_minimal(self):
        """Test loan snapshot with minimal fields"""
        snapshot = LoanSnapshot(loan_amount="$100,000")
        
        assert snapshot.loan_amount == "$100,000"
        assert snapshot.currency == "$"  # Default value


class TestLoanRecommendation:
    """Test LoanRecommendation model validation"""
    
    def test_valid_recommendation(self):
        """Test parsing valid loan recommendation"""
        data = {
            "name": "Home Purchase Loan — Fast Track",
            "type": "Home Loan (HL-PUR-001)",
            "estimated_rate": "7.5% - 8.5%",
            "estimated_em": "$3,200/month",
            "tenure": "15 years",
            "total_interest": "$436,000",
            "recommendation": "Best if you want to save on interest",
            "pros": ["Lowest total interest", "Faster payoff"],
            "cons": ["Highest monthly commitment"],
        }
        rec = LoanRecommendation(**data)
        
        assert rec.name == "Home Purchase Loan — Fast Track"
        assert len(rec.pros) == 2
        assert "Lowest total interest" in rec.pros
        assert len(rec.cons) == 1
    
    def test_recommendation_empty_lists(self):
        """Test recommendation with empty pros/cons"""
        data = {
            "name": "Simple Loan",
            "type": "Personal Loan",
            "estimated_rate": "10%",
            "estimated_em": "$500/month",
            "tenure": "2 years",
            "total_interest": "$2,000",
            "recommendation": "Good option",
        }
        rec = LoanRecommendation(**data)
        
        assert rec.pros == []
        assert rec.cons == []


class TestLoanApplication:
    """Test LoanApplication model validation"""
    
    def test_valid_application(self):
        """Test parsing valid loan application"""
        data = {
            "first_name": "Marcus",
            "last_name": "Williams",
            "email": "marcus.w@email.com",
            "phone": "+1-868-555-1234",
            "loan_type": "Home Loan",
            "loan_amount": "$400,000",
            "purpose": "Purchase property in Port of Spain",
            "employment_type": "Salaried",
            "monthly_income": "$12,000",
            "existing_debts": "Vehicle loan $1,500/month",
        }
        app = LoanApplication(**data)
        
        assert app.first_name == "Marcus"
        assert app.last_name == "Williams"
        assert app.email == "marcus.w@email.com"
        assert app.loan_amount == "$400,000"
    
    def test_application_required_fields(self):
        """Test that required fields must be present"""
        # Missing required fields should fail
        with pytest.raises(Exception):
            LoanApplication()  # No required fields


class TestDocumentsChecklist:
    """Test DocumentsChecklist model validation"""
    
    def test_checklist_with_alias_fields(self):
        """Test parsing with camelCase aliases"""
        data = {
            "requiredNow": [
                {"name": "National ID", "description": "Government ID", "required": True},
                {"name": "Pay Slips", "description": "Last 3 months", "required": True},
            ],
            "likelyLater": [
                {"name": "Property Deed", "description": "If applicable"},
            ],
        }
        checklist = DocumentsChecklist(**data)
        
        assert len(checklist.required_now) == 2
        assert checklist.required_now[0].name == "National ID"
        assert len(checklist.likely_later) == 1
    
    def test_checklist_snake_case(self):
        """Test parsing with snake_case field names"""
        data = {
            "required_now": [
                {"name": "ID", "description": "Photo ID"},
            ],
        }
        checklist = DocumentsChecklist(**data)
        
        assert len(checklist.required_now) == 1
    
    def test_checklist_empty(self):
        """Test empty checklist"""
        checklist = DocumentsChecklist()
        
        assert checklist.required_now == []
        assert checklist.likely_later == []
        assert checklist.if_applicable == []


class TestPhaseUpdate:
    """Test PhaseUpdate model validation"""
    
    def test_phase_update_with_alias(self):
        """Test parsing with phaseId alias"""
        data = {"phaseId": "phase-123", "reason": "Application submitted"}
        update = PhaseUpdate(**data)
        
        assert update.phase_id == "phase-123"
        assert update.reason == "Application submitted"
    
    def test_phase_update_minimal(self):
        """Test minimal phase update"""
        update = PhaseUpdate(phase_id="phase-456")
        
        assert update.phase_id == "phase-456"
        assert update.reason is None


class TestXMLTagParser:
    """Test XMLTagParser extraction and validation"""
    
    def test_parse_intent_analysis_tag(self):
        """Test extracting intent_analysis tag"""
        response = """
        I understand you need a home loan.
        
        <intent_analysis>
        {"purpose": "home_purchase", "loan_amount": "$400,000", "employment_type": "salaried"}
        </intent_analysis>
        
        Let me check the options.
        """
        
        parser = XMLTagParser()
        result = parser.parse(response)
        
        assert result.intent_analysis is not None
        assert result.intent_analysis.purpose == "home_purchase"
        assert result.intent_analysis.loan_amount == "$400,000"
        # Verify clean response has the text (whitespace may vary)
        assert "I understand you need a home loan." in result.clean_response
        assert "Let me check the options." in result.clean_response
        assert "<intent_analysis>" not in result.clean_response
    
    def test_parse_loan_snapshot_tag(self):
        """Test extracting loan_snapshot tag"""
        response = """
        <loan_snapshot>
        {"loan_type": "Home Loan", "loan_amount": "$400,000", "estimated_em": "$2,800/month"}
        </loan_snapshot>
        """
        
        parser = XMLTagParser()
        result = parser.parse(response)
        
        assert result.loan_snapshot is not None
        assert result.loan_snapshot.loan_type == "Home Loan"
        assert result.loan_snapshot.loan_amount == "$400,000"
    
    def test_parse_loan_recommendations_array(self):
        """Test extracting loan_recommendations array"""
        response = """
        <loan_recommendations>
        [
            {"name": "Fast Track", "type": "Home Loan", "estimated_rate": "7.5%", "estimated_em": "$3,200", "tenure": "15 years", "total_interest": "$436k", "recommendation": "Best for savings"},
            {"name": "Standard", "type": "Home Loan", "estimated_rate": "8.5%", "estimated_em": "$2,800", "tenure": "20 years", "total_interest": "$550k", "recommendation": "Balanced option"}
        ]
        </loan_recommendations>
        """
        
        parser = XMLTagParser()
        result = parser.parse(response)
        
        assert result.loan_recommendations is not None
        assert len(result.loan_recommendations) == 2
        assert result.loan_recommendations[0].name == "Fast Track"
        assert result.loan_recommendations[1].name == "Standard"
    
    def test_parse_multiple_tags(self):
        """Test extracting multiple tags from single response"""
        response = """
        <intent_analysis>
        {"purpose": "home_purchase", "monthly_income": "$8,000"}
        </intent_analysis>
        
        <loan_snapshot>
        {"loan_amount": "$400,000", "estimated_em": "$2,800/month"}
        </loan_snapshot>
        
        <loan_recommendations>
        [{"name": "Option 1", "type": "Home", "estimated_rate": "7%", "estimated_em": "$3k", "tenure": "15y", "total_interest": "$100k", "recommendation": "Good"}]
        </loan_recommendations>
        """
        
        parser = XMLTagParser()
        result = parser.parse(response)
        
        assert result.intent_analysis is not None
        assert result.loan_snapshot is not None
        assert result.loan_recommendations is not None
        assert len(result.get_all_tags_found()) == 3
    
    def test_parse_with_markdown_code_blocks(self):
        """Test normalizing JSON with markdown code blocks"""
        response = """
        <intent_analysis>
        ```json
        {"purpose": "home_purchase", "loan_amount": "$500,000"}
        ```
        </intent_analysis>
        """
        
        parser = XMLTagParser()
        result = parser.parse(response)
        
        assert result.intent_analysis is not None
        assert result.intent_analysis.purpose == "home_purchase"
        assert result.intent_analysis.loan_amount == "$500,000"
    
    def test_parse_with_curly_quotes(self):
        """Test normalizing JSON with curly quotes"""
        response = """
        <intent_analysis>
        {"purpose": "home_purchase", "note": "curly quotes test"}
        </intent_analysis>
        """
        
        parser = XMLTagParser()
        result = parser.parse(response)
        
        assert result.intent_analysis is not None
        assert result.intent_analysis.purpose == "home_purchase"
    
    def test_parse_with_trailing_commas(self):
        """Test normalizing JSON with trailing commas"""
        response = """
        <intent_analysis>
        {"purpose": "home_purchase", "loan_amount": "$400,000",}
        </intent_analysis>
        """
        
        parser = XMLTagParser()
        result = parser.parse(response)
        
        assert result.intent_analysis is not None
        assert result.intent_analysis.loan_amount == "$400,000"
    
    def test_parse_with_unquoted_keys(self):
        """Test normalizing JSON with unquoted keys"""
        response = """
        <intent_analysis>
        {purpose: "home_purchase", loan_amount: "$400,000"}
        </intent_analysis>
        """
        
        parser = XMLTagParser()
        result = parser.parse(response)
        
        assert result.intent_analysis is not None
        assert result.intent_analysis.purpose == "home_purchase"
    
    def test_parse_missing_tag(self):
        """Test handling of missing tags"""
        response = "No XML tags in this response"
        
        parser = XMLTagParser()
        result = parser.parse(response)
        
        assert result.intent_analysis is None
        assert result.loan_snapshot is None
        assert result.loan_recommendations is None
        assert len(result.parse_errors) == 0  # Missing tags are not errors
    
    def test_parse_invalid_json(self):
        """Test handling of invalid JSON"""
        response = """
        <intent_analysis>
        {this is not valid JSON}
        </intent_analysis>
        """
        
        parser = XMLTagParser()
        result = parser.parse(response)
        
        assert result.intent_analysis is None
        assert len(result.parse_errors) > 0
        assert "intent_analysis" in result.parse_errors[0]
    
    def test_parse_strict_mode_raises_exception(self):
        """Test that strict mode raises exceptions"""
        response = """
        <intent_analysis>
        {invalid json}
        </intent_analysis>
        """
        
        parser = XMLTagParser(strict_mode=True)
        
        with pytest.raises(Exception):
            parser.parse(response)
    
    def test_parse_single_tag(self):
        """Test extracting a single tag type"""
        response = """
        <intent_analysis>
        {"purpose": "auto_loan"}
        </intent_analysis>
        
        <loan_snapshot>
        {"loan_amount": "$50,000"}
        </loan_snapshot>
        """
        
        parser = XMLTagParser()
        intent = parser.parse_single(response, "intent_analysis")
        
        assert intent is not None
        assert intent.purpose == "auto_loan"
    
    def test_extract_all_tags_raw(self):
        """Test extracting all tags as raw dictionaries"""
        response = """
        <intent_analysis>
        {"purpose": "home_purchase"}
        </intent_analysis>
        
        <loan_snapshot>
        {"loan_amount": "$400,000"}
        </loan_snapshot>
        """
        
        parser = XMLTagParser()
        extracted = parser.extract_all_tags(response)
        
        assert "intent_analysis" in extracted
        assert "loan_snapshot" in extracted
        assert extracted["intent_analysis"]["purpose"] == "home_purchase"
        assert extracted["loan_snapshot"]["loan_amount"] == "$400,000"
    
    def test_case_insensitive_tags(self):
        """Test that tag matching is case-insensitive"""
        response = """
        <INTENT_ANALYSIS>
        {"purpose": "home_purchase"}
        </INTENT_ANALYSIS>
        
        <Intent_Analysis>
        {"loan_amount": "$400,000"}
        </Intent_Analysis>
        """
        
        parser = XMLTagParser()
        result = parser.parse(response)
        
        # Should find both tags (last one wins for same tag type)
        assert result.intent_analysis is not None


class TestConvenienceFunctions:
    """Test module convenience functions"""
    
    def test_parse_llm_response_function(self):
        """Test parse_llm_response convenience function"""
        response = """
        <intent_analysis>
        {"purpose": "personal_loan", "urgency": "high"}
        </intent_analysis>
        """
        
        result = parse_llm_response(response)
        
        assert result.intent_analysis is not None
        assert result.intent_analysis.purpose == "personal_loan"
        assert result.intent_analysis.urgency == "high"
    
    def test_extract_intent_function(self):
        """Test extract_intent convenience function"""
        response = """
        <intent_analysis>
        {"purpose": "business_loan", "employment_type": "self-employed"}
        </intent_analysis>
        """
        
        intent = extract_intent(response)
        
        assert intent is not None
        assert intent.purpose == "business_loan"
        assert intent.employment_type == "self-employed"
    
    def test_extract_loan_snapshot_function(self):
        """Test extract_loan_snapshot convenience function"""
        response = """
        <loan_snapshot>
        {"loan_type": "Auto Loan", "loan_amount": "$35,000"}
        </loan_snapshot>
        """
        
        snapshot = extract_loan_snapshot(response)
        
        assert snapshot is not None
        assert snapshot.loan_type == "Auto Loan"
        assert snapshot.loan_amount == "$35,000"
    
    def test_extract_recommendations_function(self):
        """Test extract_recommendations convenience function"""
        response = """
        <loan_recommendations>
        [
            {"name": "Quick Loan", "type": "Personal", "estimated_rate": "8%", "estimated_em": "$500", "tenure": "2y", "total_interest": "$2k", "recommendation": "Fast"}
        ]
        </loan_recommendations>
        """
        
        recs = extract_recommendations(response)
        
        assert recs is not None
        assert len(recs) == 1
        assert recs[0].name == "Quick Loan"


class TestParsedOutput:
    """Test ParsedOutput container"""
    
    def test_has_errors(self):
        """Test error detection"""
        output = ParsedOutput(parse_errors=["error 1", "error 2"])
        
        assert output.has_errors() is True
    
    def test_has_no_errors(self):
        """Test no errors detection"""
        output = ParsedOutput()
        
        assert output.has_errors() is False
    
    def test_has_warnings(self):
        """Test warning detection"""
        output = ParsedOutput(warnings=["warning 1"])
        
        assert output.has_warnings() is True
    
    def test_get_all_tags_found(self):
        """Test listing successfully parsed tags"""
        output = ParsedOutput(
            intent_analysis=IntentAnalysis(purpose="test"),
            loan_snapshot=LoanSnapshot(loan_amount="$100"),
            loan_recommendations=[LoanRecommendation(
                name="Test",
                type="Test",
                estimated_rate="5%",
                estimated_em="$100",
                tenure="1y",
                total_interest="$10",
                recommendation="Test"
            )],
        )
        
        tags = output.get_all_tags_found()
        
        assert "intent_analysis" in tags
        assert "loan_snapshot" in tags
        assert "loan_recommendations" in tags
        assert len(tags) == 3


class TestIntegration:
    """Integration tests with realistic LLM responses"""
    
    def test_full_lnai_style_response(self):
        """Test parsing a complete LNAI-style response"""
        response = """
        I've analyzed your financial profile and put together the ideal path for you.
        Here are your top options, with my recommendation highlighted.
        
        <intent_analysis>
        {
            "purpose": "home_purchase",
            "urgency": "medium",
            "monthly_income": "$8,000",
            "existing_debts": "Car loan $1,200/month",
            "loan_amount": "$400,000",
            "employment_type": "Salaried",
            "seriousness_score": 75,
            "fit_score": 82,
            "next_conversation_angle": "Discuss down payment and property valuation"
        }
        </intent_analysis>
        
        <loan_snapshot>
        {
            "loan_type": "Home Loan",
            "loan_amount": "$400,000",
            "estimated_em": "$2,800/month",
            "tenure": "20 years",
            "rate_band": "7.5% – 9.5%",
            "ltv": "85%",
            "currency": "$"
        }
        </loan_snapshot>
        
        <loan_recommendations>
        [
            {
                "name": "Home Purchase Loan — Fast Track",
                "type": "Home Loan (HL-PUR-001)",
                "estimated_rate": "7.5% - 8.5%",
                "estimated_em": "$3,200/month",
                "tenure": "15 years",
                "total_interest": "$436,000",
                "approval_speed": "5-7 business days",
                "pros": ["Lowest total interest", "Faster payoff"],
                "cons": ["Highest monthly commitment"],
                "recommendation": "Best if you want to save on interest and can handle higher payments"
            },
            {
                "name": "Home Purchase Loan — Standard",
                "type": "Home Loan (HL-PUR-001)",
                "estimated_rate": "8.5% - 10.5%",
                "estimated_em": "$2,800/month",
                "tenure": "20 years",
                "total_interest": "$550,000",
                "approval_speed": "5-10 business days",
                "pros": ["Manageable payments", "Moderate total cost"],
                "cons": ["Higher total interest than aggressive"],
                "recommendation": "Best if you want a balance between payments and total cost"
            }
        ]
        </loan_recommendations>
        
        Which option would you prefer to proceed with?
        """
        
        parser = XMLTagParser()
        result = parser.parse(response)
        
        # Verify no parse errors
        assert not result.has_errors()
        
        # Verify intent analysis
        assert result.intent_analysis is not None
        assert result.intent_analysis.purpose == "home_purchase"
        assert result.intent_analysis.seriousness_score == 75
        assert result.intent_analysis.fit_score == 82
        
        # Verify loan snapshot
        assert result.loan_snapshot is not None
        assert result.loan_snapshot.loan_type == "Home Loan"
        assert result.loan_snapshot.loan_amount == "$400,000"
        
        # Verify recommendations
        assert result.loan_recommendations is not None
        assert len(result.loan_recommendations) == 2
        assert "Fast Track" in result.loan_recommendations[0].name
        assert "Standard" in result.loan_recommendations[1].name
        
        # Verify clean response
        assert "<intent_analysis>" not in result.clean_response
        assert "<loan_snapshot>" not in result.clean_response
        assert "<loan_recommendations>" not in result.clean_response
        assert "Which option would you prefer" in result.clean_response
    
    def test_application_submission_response(self):
        """Test parsing application submission response"""
        response = """
        Excellent! Your application has been submitted successfully.
        
        <loan_application>
        {
            "first_name": "Marcus",
            "last_name": "Williams",
            "email": "marcus.w@email.com",
            "phone": "+1-868-555-1234",
            "loan_type": "Home Loan",
            "loan_amount": "$400,000",
            "purpose": "Purchase property in Port of Spain",
            "employment_type": "Salaried",
            "monthly_income": "$12,000",
            "existing_debts": "Vehicle loan $1,500/month"
        }
        </loan_application>
        
        <documents_checklist>
        {
            "requiredNow": [
                {"name": "National ID or Passport", "description": "Government-issued photo ID", "required": true},
                {"name": "Job Letter", "description": "From current employer, < 3 months", "required": true}
            ]
        }
        </documents_checklist>
        
        Please upload the required documents using the attachment button below.
        """
        
        parser = XMLTagParser()
        result = parser.parse(response)
        
        assert result.loan_application is not None
        assert result.loan_application.first_name == "Marcus"
        assert result.loan_application.last_name == "Williams"
        
        assert result.documents_checklist is not None
        assert len(result.documents_checklist.required_now) == 2
        assert result.documents_checklist.required_now[0].name == "National ID or Passport"


# ─────────────────────────────────────────────────────────────────────────────
# Run Tests
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
