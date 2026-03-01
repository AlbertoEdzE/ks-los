import pytest
import os
from src.core.knowledge_base import KnowledgeBase

# Scientific Validation: Integration Test with Real Infrastructure
# Requires: Docker (Postgres) and Ollama (nomic-embed-text) running.

@pytest.mark.integration
def test_knowledge_base_integration():
    """
    Validates that the Knowledge Base correctly ingests and retrieves information
    using the real vector database and embedding model.
    """
    # 1. Setup
    kb = KnowledgeBase()
    kb.clear() # Start fresh
    
    # 2. Ingest Data (Hypothesis: Data ingested is retrievable)
    test_content_path = "temp_test_policy.md"
    with open(test_content_path, "w") as f:
        f.write("# Test Policy\n\n## 1. Rules\nMaximum debt-to-income ratio is 45%.\n\n## 2. Exceptions\nSuper Prime borrowers can go up to 50%.")
    
    try:
        kb.ingest_document(test_content_path)
        
        # 3. Experiment: Retrieval Accuracy
        # Query 1: Standard rule
        results = kb.query("What is the max DTI?", k=1)
        assert len(results) > 0
        assert "45%" in results[0].page_content
        
        # Query 2: Exception
        results = kb.query("Super Prime exception", k=1)
        assert len(results) > 0
        assert "50%" in results[0].page_content
        
    finally:
        # 4. Teardown
        if os.path.exists(test_content_path):
            os.remove(test_content_path)
        kb.clear()
