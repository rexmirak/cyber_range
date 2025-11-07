"""
RAG (Retrieval-Augmented Generation) Pipeline

Provides context retrieval for LLM queries using local embeddings and vector search.
"""

import json
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np


@dataclass
class Document:
    """A document in the knowledge base"""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None


@dataclass
class SearchResult:
    """A search result with relevance score"""
    document: Document
    score: float


class LocalRAG:
    """
    Local RAG pipeline using embeddings and vector similarity
    
    Features:
    - Local embeddings (no external API)
    - SQLite storage for documents and embeddings
    - Cosine similarity search
    - Supports scenario docs, module docs, and technique guides
    """

    def __init__(self, db_path: str = ".cyber_range/rag.db", embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize RAG pipeline
        
        Args:
            db_path: Path to SQLite database
            embedding_model: Sentence transformer model name
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedding_model_name = embedding_model
        self._embedding_model = None
        self._init_db()

    @property
    def embedding_model(self):
        """Lazy load embedding model"""
        if self._embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer(self.embedding_model_name)
            except ImportError:
                raise RuntimeError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
        return self._embedding_model

    def _init_db(self) -> None:
        """Initialize SQLite database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    embedding BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata ON documents(metadata)
            """)
            conn.commit()

    def add_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> str:
        """
        Add a document to the knowledge base
        
        Args:
            content: Document content
            metadata: Optional metadata
            doc_id: Optional document ID (auto-generated if not provided)
            
        Returns:
            Document ID
        """
        if doc_id is None:
            doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]

        metadata = metadata or {}
        embedding = self._compute_embedding(content)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO documents (id, content, metadata, embedding)
                VALUES (?, ?, ?, ?)
                """,
                (doc_id, content, json.dumps(metadata), self._serialize_embedding(embedding))
            )
            conn.commit()
        
        return doc_id

    def add_documents(self, documents: List[Tuple[str, Dict[str, Any]]]) -> List[str]:
        """
        Add multiple documents in batch
        
        Args:
            documents: List of (content, metadata) tuples
            
        Returns:
            List of document IDs
        """
        doc_ids = []
        contents = [doc[0] for doc in documents]
        embeddings = self._compute_embeddings_batch(contents)
        
        with sqlite3.connect(self.db_path) as conn:
            for (content, metadata), embedding in zip(documents, embeddings):
                doc_id = hashlib.sha256(content.encode()).hexdigest()[:16]
                conn.execute(
                    """
                    INSERT OR REPLACE INTO documents (id, content, metadata, embedding)
                    VALUES (?, ?, ?, ?)
                    """,
                    (doc_id, content, json.dumps(metadata), self._serialize_embedding(embedding))
                )
                doc_ids.append(doc_id)
            conn.commit()
        
        return doc_ids

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """
        Search for relevant documents
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            List of search results with scores
        """
        query_embedding = self._compute_embedding(query)
        
        with sqlite3.connect(self.db_path) as conn:
            if filter_metadata:
                # Simple metadata filtering (can be enhanced)
                metadata_json = json.dumps(filter_metadata)
                cursor = conn.execute(
                    "SELECT id, content, metadata, embedding FROM documents WHERE metadata LIKE ?",
                    (f"%{metadata_json}%",)
                )
            else:
                cursor = conn.execute(
                    "SELECT id, content, metadata, embedding FROM documents"
                )
            
            results = []
            for row in cursor.fetchall():
                doc_id, content, metadata_str, embedding_blob = row
                embedding = self._deserialize_embedding(embedding_blob)
                
                # Compute cosine similarity
                score = self._cosine_similarity(query_embedding, embedding)
                
                doc = Document(
                    id=doc_id,
                    content=content,
                    metadata=json.loads(metadata_str),
                    embedding=embedding
                )
                results.append(SearchResult(document=doc, score=score))
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def get_context(
        self,
        query: str,
        top_k: int = 3,
        max_chars: int = 2000,
    ) -> str:
        """
        Get formatted context for LLM prompt
        
        Args:
            query: Query for context retrieval
            top_k: Number of documents to retrieve
            max_chars: Maximum characters in context
            
        Returns:
            Formatted context string
        """
        results = self.search(query, top_k=top_k)
        
        context_parts = []
        total_chars = 0
        
        for result in results:
            content = result.document.content
            if total_chars + len(content) > max_chars:
                # Truncate last document to fit
                remaining = max_chars - total_chars
                content = content[:remaining] + "..."
                context_parts.append(content)
                break
            
            context_parts.append(content)
            total_chars += len(content)
        
        return "\n\n---\n\n".join(context_parts)

    def _compute_embedding(self, text: str) -> np.ndarray:
        """Compute embedding for a single text"""
        return self.embedding_model.encode(text, convert_to_numpy=True)

    def _compute_embeddings_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Compute embeddings for multiple texts"""
        return self.embedding_model.encode(texts, convert_to_numpy=True, show_progress_bar=True)

    def _serialize_embedding(self, embedding: np.ndarray) -> bytes:
        """Serialize embedding to bytes for storage"""
        return embedding.tobytes()

    def _deserialize_embedding(self, data: bytes) -> np.ndarray:
        """Deserialize embedding from bytes"""
        return np.frombuffer(data, dtype=np.float32)

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors"""
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def index_scenario(self, scenario: Dict[str, Any]) -> List[str]:
        """
        Index a scenario for retrieval
        
        Args:
            scenario: Scenario JSON
            
        Returns:
            List of indexed document IDs
        """
        doc_ids = []
        
        # Index metadata and narrative
        meta = scenario.get("metadata", {})
        narrative = scenario.get("narrative", {})
        
        doc_ids.append(self.add_document(
            content=f"""
Scenario: {meta.get('name')}
Description: {meta.get('description')}
Learning Objectives: {', '.join(meta.get('learning_objectives', []))}
Background: {narrative.get('scenario_background')}
Objectives: {', '.join(narrative.get('objectives', []))}
            """.strip(),
            metadata={"type": "scenario_overview", "scenario_name": meta.get('name')}
        ))
        
        # Index vulnerabilities
        for vuln in scenario.get("vulnerabilities", []):
            doc_ids.append(self.add_document(
                content=f"""
Vulnerability: {vuln.get('name')}
Type: {vuln.get('type')}
Severity: {vuln.get('severity')}
Description: {vuln.get('description')}
Exploitation: {vuln.get('exploitation_notes', 'N/A')}
Remediation: {vuln.get('remediation', 'N/A')}
                """.strip(),
                metadata={"type": "vulnerability", "vuln_type": vuln.get('type')}
            ))
        
        # Index services
        for service in scenario.get("services", []):
            doc_ids.append(self.add_document(
                content=f"""
Service: {service.get('name')}
Type: {service.get('type')}
Version: {service.get('version')}
                """.strip(),
                metadata={"type": "service", "service_type": service.get('type')}
            ))
        
        return doc_ids

    def index_knowledge_base(self, kb_dir: Path) -> int:
        """
        Index markdown files from knowledge base directory
        
        Args:
            kb_dir: Directory containing markdown files
            
        Returns:
            Number of documents indexed
        """
        kb_dir = Path(kb_dir)
        if not kb_dir.exists():
            return 0
        
        documents = []
        for md_file in kb_dir.rglob("*.md"):
            content = md_file.read_text()
            metadata = {
                "type": "knowledge_base",
                "filename": md_file.name,
                "path": str(md_file)
            }
            documents.append((content, metadata))
        
        if documents:
            self.add_documents(documents)
        
        return len(documents)

    def clear(self) -> None:
        """Clear all documents from the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM documents")
            conn.commit()
