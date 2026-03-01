import pytest
from unittest.mock import patch, MagicMock
from src.core.knowledge_base import KnowledgeBase

@patch("src.core.knowledge_base.PGVector")
@patch("src.core.knowledge_base.OllamaEmbeddings")
def test_knowledge_base_initialization(mock_embeddings, mock_pgvector):
    """Test KB initialization."""
    kb = KnowledgeBase()
    assert kb.vector_store is not None
    mock_embeddings.assert_called_once()
    mock_pgvector.assert_called_once()

@patch("src.core.knowledge_base.PGVector")
@patch("src.core.knowledge_base.OllamaEmbeddings")
def test_ingest_document(mock_embeddings, mock_pgvector):
    """Test document ingestion."""
    kb = KnowledgeBase()
    kb.vector_store = MagicMock()
    
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "## Section 1\nContent"
        
        kb.ingest_document("fake_path.md")
        
        kb.vector_store.add_documents.assert_called_once()
        args = kb.vector_store.add_documents.call_args[0][0]
        assert len(args) > 0
        assert args[0].page_content == "## Section 1\nContent"

@patch("src.core.knowledge_base.PGVector")
@patch("src.core.knowledge_base.OllamaEmbeddings")
def test_query(mock_embeddings, mock_pgvector):
    """Test querying."""
    kb = KnowledgeBase()
    kb.vector_store = MagicMock()
    kb.vector_store.similarity_search.return_value = [MagicMock(page_content="result")]
    
    results = kb.query("test query")
    assert len(results) == 1
    assert results[0].page_content == "result"
    kb.vector_store.similarity_search.assert_called_with("test query", k=3)
