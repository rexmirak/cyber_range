"""
Unit tests for Ollama Adapter

Tests connection, generation, JSON extraction, and error handling.
"""

import pytest
from unittest.mock import Mock, patch  # MagicMock unused
import requests

from src.llm.adapter import OllamaAdapter, HintTier, LLMConfig


class TestOllamaAdapter:
    """Test suite for OllamaAdapter"""

    @patch('src.llm.adapter.requests.get')
    def test_verify_connection_success(self, mock_get):
        """Test successful connection verification"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [{"name": "llama3.2:latest"}]
        }
        mock_get.return_value = mock_response
        
        # Should not raise
        adapter = OllamaAdapter()
        assert adapter.config.model == "llama3.2:latest"

    @patch('src.llm.adapter.requests.get')
    def test_verify_connection_model_not_found(self, mock_get):
        """Test connection when model is not available"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [{"name": "other-model"}]
        }
        mock_get.return_value = mock_response
        
        with pytest.raises(RuntimeError, match="Model llama3.2:latest not found"):
            OllamaAdapter()

    @patch('src.llm.adapter.requests.get')
    def test_verify_connection_ollama_not_running(self, mock_get):
        """Test connection when Ollama is not running"""
        mock_get.side_effect = requests.exceptions.ConnectionError()
        
        with pytest.raises(RuntimeError, match="Cannot connect to Ollama"):
            OllamaAdapter()

    @patch('src.llm.adapter.requests.get')
    @patch('src.llm.adapter.requests.post')
    def test_generate_basic(self, mock_post, mock_get):
        """Test basic text generation"""
        # Mock connection verification
        mock_get.return_value = Mock(json=lambda: {"models": [{"name": "llama3.2:latest"}]})
        
        # Mock generation
        mock_post.return_value = Mock(json=lambda: {"response": "Generated text"})
        
        adapter = OllamaAdapter()
        result = adapter._generate("Test prompt")
        
        assert result == "Generated text"
        mock_post.assert_called_once()

    @patch('src.llm.adapter.requests.get')
    @patch('src.llm.adapter.requests.post')
    def test_generate_with_system_message(self, mock_post, mock_get):
        """Test generation with system message"""
        mock_get.return_value = Mock(json=lambda: {"models": [{"name": "llama3.2:latest"}]})
        mock_post.return_value = Mock(json=lambda: {"response": "Response"})
        
        adapter = OllamaAdapter()
        adapter._generate("Prompt", system="System instructions")
        
        # Verify system message was included
        call_args = mock_post.call_args
        assert call_args[1]['json']['system'] == "System instructions"

    @patch('src.llm.adapter.requests.get')
    @patch('src.llm.adapter.requests.post')
    def test_generate_timeout(self, mock_post, mock_get):
        """Test generation timeout handling"""
        mock_get.return_value = Mock(json=lambda: {"models": [{"name": "llama3.2:latest"}]})
        mock_post.side_effect = requests.exceptions.Timeout()
        
        adapter = OllamaAdapter()
        
        with pytest.raises(RuntimeError, match="timed out"):
            adapter._generate("Prompt")

    def test_extract_json_plain(self):
        """Test JSON extraction from plain text"""
        adapter = Mock(spec=OllamaAdapter)
        adapter._extract_json = OllamaAdapter._extract_json.__get__(adapter, OllamaAdapter)
        
        json_str = '{"key": "value"}'
        result = adapter._extract_json(json_str)
        assert result == json_str

    def test_extract_json_with_markdown(self):
        """Test JSON extraction from markdown code block"""
        adapter = Mock(spec=OllamaAdapter)
        adapter._extract_json = OllamaAdapter._extract_json.__get__(adapter, OllamaAdapter)
        
        response = '```json\n{"key": "value"}\n```'
        result = adapter._extract_json(response)
        assert result == '{"key": "value"}'

    def test_extract_json_with_generic_markdown(self):
        """Test JSON extraction from generic code block"""
        adapter = Mock(spec=OllamaAdapter)
        adapter._extract_json = OllamaAdapter._extract_json.__get__(adapter, OllamaAdapter)
        
        response = '```\n{"key": "value"}\n```'
        result = adapter._extract_json(response)
        assert result == '{"key": "value"}'

    def test_extract_json_invalid(self):
        """Test JSON extraction with invalid JSON"""
        adapter = Mock(spec=OllamaAdapter)
        adapter._extract_json = OllamaAdapter._extract_json.__get__(adapter, OllamaAdapter)
        
        with pytest.raises(ValueError, match="did not return valid JSON"):
            adapter._extract_json("not json at all")

    @patch('src.llm.adapter.requests.get')
    @patch('src.llm.adapter.requests.post')
    def test_generate_scenario_json(self, mock_post, mock_get):
        """Test scenario JSON generation"""
        mock_get.return_value = Mock(json=lambda: {"models": [{"name": "llama3.2:latest"}]})
        
        valid_json = '{"metadata": {"name": "Test"}}'
        mock_post.return_value = Mock(json=lambda: {"response": valid_json})
        
        adapter = OllamaAdapter()
        
        with patch('src.llm.prompts.build_authoring_prompt') as mock_prompt:
            mock_prompt.return_value = "Built prompt"
            
            result = adapter.generate_scenario_json(
                user_description="Test scenario",
                schema={},
                enums={},
            )
            
            assert result == valid_json
            mock_prompt.assert_called_once()

    @patch('src.llm.adapter.requests.get')
    @patch('src.llm.adapter.requests.post')
    def test_repair_scenario_json(self, mock_post, mock_get):
        """Test scenario JSON repair"""
        mock_get.return_value = Mock(json=lambda: {"models": [{"name": "llama3.2:latest"}]})
        
        fixed_json = '{"metadata": {"name": "Fixed"}}'
        mock_post.return_value = Mock(json=lambda: {"response": fixed_json})
        
        adapter = OllamaAdapter()
        
        with patch('src.llm.prompts.build_repair_prompt') as mock_prompt:
            mock_prompt.return_value = "Built prompt"
            
            result = adapter.repair_scenario_json(
                broken_json='{"bad": json}',
                errors=["Error 1"],
                schema={},
            )
            
            assert result == fixed_json

    @patch('src.llm.adapter.requests.get')
    @patch('src.llm.adapter.requests.post')
    def test_suggest_hint(self, mock_post, mock_get):
        """Test hint generation"""
        mock_get.return_value = Mock(json=lambda: {"models": [{"name": "llama3.2:latest"}]})
        mock_post.return_value = Mock(json=lambda: {"response": "Helpful hint"})
        
        adapter = OllamaAdapter()
        
        with patch('src.llm.prompts.build_hint_prompt') as mock_prompt:
            mock_prompt.return_value = "Built prompt"
            
            result = adapter.suggest_hint(
                scenario={},
                lab_state={},
                tier=HintTier.NUDGE,
            )
            
            assert result == "Helpful hint"

    @patch('src.llm.adapter.requests.get')
    @patch('src.llm.adapter.requests.post')
    def test_explain_concept(self, mock_post, mock_get):
        """Test concept explanation"""
        mock_get.return_value = Mock(json=lambda: {"models": [{"name": "llama3.2:latest"}]})
        mock_post.return_value = Mock(json=lambda: {"response": "Detailed explanation"})
        
        adapter = OllamaAdapter()
        
        with patch('src.llm.prompts.build_explanation_prompt') as mock_prompt:
            mock_prompt.return_value = "Built prompt"
            
            result = adapter.explain_concept(
                topic="SQL Injection",
                context={},
            )
            
            assert result == "Detailed explanation"

    @patch('src.llm.adapter.requests.get')
    @patch('src.llm.adapter.requests.post')
    def test_chat(self, mock_post, mock_get):
        """Test multi-turn chat"""
        mock_get.return_value = Mock(json=lambda: {"models": [{"name": "llama3.2:latest"}]})
        mock_post.return_value = Mock(json=lambda: {"response": "Chat response"})
        
        adapter = OllamaAdapter()
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"},
        ]
        
        result = adapter.chat(messages)
        assert result == "Chat response"


class TestLLMConfig:
    """Test LLMConfig dataclass"""

    def test_default_config(self):
        """Test default configuration values"""
        config = LLMConfig()
        assert config.base_url == "http://localhost:11434"
        assert config.model == "llama3.2:latest"
        assert config.temperature == 0.2
        assert config.timeout == 120

    def test_custom_config(self):
        """Test custom configuration"""
        config = LLMConfig(
            base_url="http://custom:8080",
            model="custom-model",
            temperature=0.5,
            timeout=60,
        )
        assert config.base_url == "http://custom:8080"
        assert config.model == "custom-model"
        assert config.temperature == 0.5
        assert config.timeout == 60


class TestHintTier:
    """Test HintTier enum"""

    def test_hint_tier_values(self):
        """Test hint tier enum values"""
        assert HintTier.NUDGE.value == 0
        assert HintTier.DIRECTIONAL.value == 1
        assert HintTier.TECHNIQUE.value == 2
        assert HintTier.DETAILED.value == 3

    def test_hint_tier_names(self):
        """Test hint tier enum names"""
        assert HintTier.NUDGE.name == "NUDGE"
        assert HintTier.DIRECTIONAL.name == "DIRECTIONAL"
        assert HintTier.TECHNIQUE.name == "TECHNIQUE"
        assert HintTier.DETAILED.name == "DETAILED"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
