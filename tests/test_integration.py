"""
Integration Test for Phase 2 LLM Components

Tests the complete workflow from authoring to hints.
Note: Requires Ollama running with llama3.2:latest
"""

import pytest
import json
from pathlib import Path

from src.llm.integration import LLMIntegration
from src.llm.adapter import HintTier


# Mark as integration test (can be skipped with: pytest -m "not integration")
pytestmark = pytest.mark.integration


@pytest.fixture
def llm():
    """Create LLM integration instance"""
    try:
        return LLMIntegration(enable_rag=False)
    except RuntimeError as e:
        pytest.skip(f"Ollama not available: {e}")


@pytest.fixture
def schema():
    """Load JSON schema"""
    schema_path = Path("schema/scenario.schema.json")
    if not schema_path.exists():
        pytest.skip("Schema file not found")
    return json.loads(schema_path.read_text())


@pytest.fixture
def enums():
    """Define available enums"""
    return {
        "difficulty": ["easy", "medium", "hard"],
        "host_type": ["attacker", "victim", "web", "db", "ftp", "smb", "custom"],
        "service_type": ["nginx", "apache", "flask", "node", "mysql", "postgres", "vsftpd", "openssh", "samba", "custom"],
        "vuln_type": ["weak_password", "outdated_software", "misconfiguration", "default_creds", "exposed_service", 
                      "vulnerable_webapp", "directory_traversal", "sql_injection", "command_injection", "ssrf", "lateral_movement"],
        "network_type": ["bridge", "custom_bridge", "isolated", "public"],
    }


class TestLLMIntegration:
    """Integration tests for LLM features"""

    @pytest.mark.slow
    def test_simple_scenario_generation(self, llm, schema, enums):
        """Test generating a simple scenario (slow test)"""
        description = "Create a simple web server with SQL injection, easy difficulty"
        
        try:
            scenario = llm.author_scenario(
                user_description=description,
                schema=schema,
                enums=enums,
                use_few_shot=True,
            )
            
            # The LLM might wrap the scenario in extra keys, extract it
            if "scenario" in scenario and isinstance(scenario["scenario"], dict):
                scenario = scenario["scenario"]
            
            # Verify basic structure
            assert "metadata" in scenario, f"No metadata in: {list(scenario.keys())}"
            assert "networks" in scenario
            assert "hosts" in scenario
            assert "flags" in scenario
            
            # Verify metadata
            assert scenario["metadata"]["difficulty"] in ["easy", "medium", "hard"]
            
            print("\n✅ Generated scenario successfully")
            print(f"Scenario name: {scenario['metadata'].get('name')}")
            
        except Exception as e:
            pytest.fail(f"Scenario generation failed: {e}")

    def test_hint_generation(self, llm):
        """Test generating hints at different tiers"""
        scenario = {
            "metadata": {"name": "Test Lab"},
            "narrative": {"objectives": ["Find SQL injection", "Extract password"]},
        }
        
        lab_state = {
            "hosts": {"web": {"ip": "172.20.0.20", "status": "running"}},
            "solved_flags": [],
        }
        
        # Test each hint tier
        for tier in [HintTier.NUDGE, HintTier.DIRECTIONAL]:
            try:
                hint = llm.provide_hint(scenario, lab_state, tier)
                
                assert isinstance(hint, str)
                assert len(hint) > 0
                
                print(f"\n✅ Tier {tier.value} ({tier.name}) hint generated")
                print(f"Hint preview: {hint[:100]}...")
                
            except Exception as e:
                pytest.fail(f"Hint generation failed for tier {tier.name}: {e}")

    def test_explanation(self, llm):
        """Test generating an explanation"""
        topic = "SQL Injection"
        context = {
            "scenario": {
                "metadata": {"name": "SQL Injection Lab"},
                "vulnerabilities": [
                    {"type": "sql_injection", "description": "Login form vulnerable to SQLi"}
                ]
            }
        }
        
        try:
            explanation = llm.explain_topic(topic, context)
            
            assert isinstance(explanation, str)
            assert len(explanation) > 100  # Should be substantial
            assert "SQL" in explanation or "injection" in explanation.lower()
            
            print("\n✅ Explanation generated successfully")
            print(f"Explanation length: {len(explanation)} chars")
            
        except Exception as e:
            pytest.fail(f"Explanation generation failed: {e}")


class TestRAGIntegration:
    """Integration tests for RAG pipeline"""

    @pytest.fixture
    def llm_with_rag(self, tmp_path):
        """Create LLM with RAG enabled"""
        db_path = tmp_path / "test_rag.db"
        try:
            return LLMIntegration(rag_db_path=str(db_path), enable_rag=True)
        except RuntimeError as e:
            pytest.skip(f"Ollama not available: {e}")

    def test_scenario_indexing(self, llm_with_rag):
        """Test indexing a scenario"""
        scenario = {
            "metadata": {
                "name": "Test Scenario",
                "description": "A test scenario for indexing",
                "learning_objectives": ["Learn SQL injection"],
            },
            "narrative": {
                "scenario_background": "Background story",
                "objectives": ["Objective 1"],
            },
            "vulnerabilities": [
                {
                    "name": "SQL Injection",
                    "type": "sql_injection",
                    "severity": "high",
                    "description": "Vulnerable login form",
                }
            ],
            "services": [],
        }
        
        doc_ids = llm_with_rag.index_scenario(scenario)
        
        assert len(doc_ids) >= 2  # At least overview and vulnerability
        print(f"\n✅ Indexed {len(doc_ids)} documents from scenario")

    def test_rag_enhanced_hint(self, llm_with_rag):
        """Test hint generation with RAG context"""
        # Index some relevant docs
        scenario = {
            "metadata": {"name": "SQL Lab", "description": "SQL injection practice"},
            "narrative": {"objectives": ["Find SQLi"]},
            "vulnerabilities": [
                {
                    "name": "SQLi",
                    "type": "sql_injection",
                    "description": "SQL injection vulnerability",
                }
            ],
            "services": [],
        }
        
        llm_with_rag.index_scenario(scenario)
        
        # Generate hint
        lab_state = {"hosts": {}, "solved_flags": []}
        
        try:
            hint = llm_with_rag.provide_hint(scenario, lab_state, HintTier.NUDGE)
            
            assert isinstance(hint, str)
            assert len(hint) > 0
            
            print("\n✅ RAG-enhanced hint generated")
            
        except Exception as e:
            pytest.fail(f"RAG-enhanced hint failed: {e}")


def test_check_ollama_connection():
    """Sanity check: verify Ollama is accessible"""
    try:
        from src.llm.adapter import OllamaAdapter
        adapter = OllamaAdapter()
        print("\n✅ Ollama connection successful")
        print(f"Model: {adapter.config.model}")
        print(f"Base URL: {adapter.config.base_url}")
    except RuntimeError as e:
        pytest.skip(f"Ollama not available: {e}")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
