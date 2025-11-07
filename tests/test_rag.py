"""
Unit tests for RAG Pipeline

Tests document indexing, search, and retrieval.
"""

import pytest
import json
from pathlib import Path
import tempfile
import shutil
import numpy as np

from src.llm.rag import LocalRAG, Document, SearchResult


class TestLocalRAG:
    """Test suite for LocalRAG"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        temp_dir = tempfile.mkdtemp()
        db_path = Path(temp_dir) / "test_rag.db"
        yield str(db_path)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def rag(self, temp_db):
        """Create RAG instance with temporary database"""
        return LocalRAG(db_path=temp_db)

    def test_initialization(self, temp_db):
        """Test RAG pipeline initialization"""
        rag = LocalRAG(db_path=temp_db)
        assert Path(temp_db).exists()
        assert rag.embedding_model_name == "all-MiniLM-L6-v2"

    def test_add_document(self, rag):
        """Test adding a single document"""
        doc_id = rag.add_document(
            content="SQL injection is a web vulnerability",
            metadata={"type": "tutorial", "topic": "sqli"}
        )
        
        assert doc_id is not None
        assert len(doc_id) == 16  # SHA256 first 16 chars

    def test_add_document_with_custom_id(self, rag):
        """Test adding document with custom ID"""
        custom_id = "doc_001"
        doc_id = rag.add_document(
            content="Test content",
            metadata={},
            doc_id=custom_id
        )
        
        assert doc_id == custom_id

    def test_add_documents_batch(self, rag):
        """Test batch document addition"""
        documents = [
            ("Document 1 about SQL injection", {"type": "tutorial"}),
            ("Document 2 about XSS attacks", {"type": "tutorial"}),
            ("Document 3 about CSRF", {"type": "tutorial"}),
        ]
        
        doc_ids = rag.add_documents(documents)
        
        assert len(doc_ids) == 3
        assert all(len(doc_id) == 16 for doc_id in doc_ids)

    def test_search_basic(self, rag):
        """Test basic search functionality"""
        # Add documents
        rag.add_document("SQL injection tutorial", {"type": "guide"})
        rag.add_document("Cross-site scripting guide", {"type": "guide"})
        rag.add_document("Buffer overflow explanation", {"type": "guide"})
        
        # Search
        results = rag.search("SQL attack", top_k=2)
        
        assert len(results) <= 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(isinstance(r.document, Document) for r in results)
        assert all(isinstance(r.score, float) for r in results)

    def test_search_relevance(self, rag):
        """Test that search returns relevant results"""
        rag.add_document("SQL injection is a database vulnerability", {"type": "guide"})
        rag.add_document("XSS is a browser vulnerability", {"type": "guide"})
        
        results = rag.search("database attack", top_k=1)
        
        assert len(results) == 1
        assert "SQL" in results[0].document.content or "database" in results[0].document.content

    def test_search_no_results(self, rag):
        """Test search with no documents"""
        results = rag.search("anything", top_k=5)
        assert len(results) == 0

    def test_get_context(self, rag):
        """Test context retrieval for prompts"""
        rag.add_document("Short document", {})
        rag.add_document("Another short doc", {})
        
        context = rag.get_context("document", top_k=2, max_chars=100)
        
        assert isinstance(context, str)
        assert len(context) <= 120  # Some overhead for separators

    def test_get_context_truncation(self, rag):
        """Test that context is truncated appropriately"""
        long_doc = "A" * 1000
        rag.add_document(long_doc, {})
        
        context = rag.get_context("A", top_k=1, max_chars=100)
        
        assert len(context) <= 103  # max_chars + "..."
        assert context.endswith("...")

    def test_index_scenario(self, rag):
        """Test indexing a scenario"""
        scenario = {
            "metadata": {
                "name": "Test Lab",
                "description": "A test scenario",
                "learning_objectives": ["Learn SQL injection"],
            },
            "narrative": {
                "scenario_background": "Background story",
                "objectives": ["Exploit the vulnerability"],
            },
            "vulnerabilities": [
                {
                    "name": "SQL Injection",
                    "type": "sql_injection",
                    "severity": "high",
                    "description": "Login form is vulnerable",
                    "exploitation_notes": "Use common payloads",
                    "remediation": "Use parameterized queries",
                }
            ],
            "services": [
                {
                    "name": "Web Server",
                    "type": "apache",
                    "version": "2.4",
                }
            ],
        }
        
        doc_ids = rag.index_scenario(scenario)
        
        assert len(doc_ids) >= 3  # Overview, vulnerability, service
        
        # Verify we can search for indexed content
        results = rag.search("SQL injection", top_k=2)
        assert len(results) > 0

    def test_index_knowledge_base(self, rag):
        """Test indexing markdown files from directory"""
        temp_dir = tempfile.mkdtemp()
        kb_dir = Path(temp_dir) / "kb"
        kb_dir.mkdir()
        
        # Create test markdown files
        (kb_dir / "doc1.md").write_text("# SQL Injection\n\nSQL injection tutorial")
        (kb_dir / "doc2.md").write_text("# XSS\n\nCross-site scripting guide")
        
        count = rag.index_knowledge_base(kb_dir)
        
        assert count == 2
        
        # Verify searchable
        results = rag.search("SQL", top_k=1)
        assert len(results) > 0
        
        shutil.rmtree(temp_dir)

    def test_index_knowledge_base_empty_dir(self, rag):
        """Test indexing empty directory"""
        temp_dir = tempfile.mkdtemp()
        count = rag.index_knowledge_base(Path(temp_dir))
        assert count == 0
        shutil.rmtree(temp_dir)

    def test_index_knowledge_base_nonexistent(self, rag):
        """Test indexing nonexistent directory"""
        count = rag.index_knowledge_base(Path("/nonexistent/path"))
        assert count == 0

    def test_clear(self, rag):
        """Test clearing all documents"""
        rag.add_document("Test document", {})
        rag.add_document("Another document", {})
        
        results_before = rag.search("document", top_k=5)
        assert len(results_before) == 2
        
        rag.clear()
        
        results_after = rag.search("document", top_k=5)
        assert len(results_after) == 0

    def test_compute_embedding(self, rag):
        """Test embedding computation"""
        text = "Test text for embedding"
        embedding = rag._compute_embedding(text)
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape[0] == 384  # all-MiniLM-L6-v2 dimension

    def test_compute_embeddings_batch(self, rag):
        """Test batch embedding computation"""
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = rag._compute_embeddings_batch(texts)
        
        assert len(embeddings) == 3
        assert all(isinstance(emb, np.ndarray) for emb in embeddings)
        assert all(emb.shape[0] == 384 for emb in embeddings)

    def test_cosine_similarity(self, rag):
        """Test cosine similarity calculation"""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        vec3 = np.array([0.0, 1.0, 0.0])
        
        # Identical vectors
        sim1 = rag._cosine_similarity(vec1, vec2)
        assert abs(sim1 - 1.0) < 0.001
        
        # Orthogonal vectors
        sim2 = rag._cosine_similarity(vec1, vec3)
        assert abs(sim2 - 0.0) < 0.001

    def test_serialize_deserialize_embedding(self, rag):
        """Test embedding serialization and deserialization"""
        original = np.random.rand(384).astype(np.float32)
        
        serialized = rag._serialize_embedding(original)
        assert isinstance(serialized, bytes)
        
        deserialized = rag._deserialize_embedding(serialized)
        assert isinstance(deserialized, np.ndarray)
        assert np.allclose(original, deserialized)


class TestDocument:
    """Test Document dataclass"""

    def test_document_creation(self):
        """Test creating a document"""
        doc = Document(
            id="doc_001",
            content="Test content",
            metadata={"type": "test"},
        )
        
        assert doc.id == "doc_001"
        assert doc.content == "Test content"
        assert doc.metadata == {"type": "test"}
        assert doc.embedding is None

    def test_document_with_embedding(self):
        """Test document with embedding"""
        embedding = np.array([1.0, 2.0, 3.0])
        doc = Document(
            id="doc_001",
            content="Test",
            metadata={},
            embedding=embedding,
        )
        
        assert np.array_equal(doc.embedding, embedding)


class TestSearchResult:
    """Test SearchResult dataclass"""

    def test_search_result_creation(self):
        """Test creating a search result"""
        doc = Document(id="1", content="Test", metadata={})
        result = SearchResult(document=doc, score=0.95)
        
        assert result.document == doc
        assert result.score == 0.95


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
