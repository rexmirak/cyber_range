"""
Unit tests for Tool Registry

Tests safe tools for LLM interaction.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock

from src.llm.tools import (
    Tool,
    ToolResult,
    GetDocsTool,
    GetStateTool,
    ValidateJSONTool,
    DiffJSONTool,
    ToolRegistry,
    create_tool_registry,
)


class TestToolResult:
    """Test ToolResult dataclass"""

    def test_success_result(self):
        """Test successful tool result"""
        result = ToolResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None

    def test_failure_result(self):
        """Test failed tool result"""
        result = ToolResult(success=False, data=None, error="Something went wrong")
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"


class TestGetDocsTool:
    """Test GetDocsTool"""

    def test_tool_properties(self):
        """Test tool name and description"""
        mock_rag = Mock()
        tool = GetDocsTool(mock_rag)
        
        assert tool.name == "get_docs"
        assert isinstance(tool.description, str)
        assert len(tool.description) > 0

    def test_execute_success(self):
        """Test successful document retrieval"""
        mock_rag = Mock()
        mock_rag.get_context.return_value = "Retrieved context"
        
        tool = GetDocsTool(mock_rag)
        result = tool.execute(query="test query", top_k=3)
        
        assert result.success is True
        assert result.data == {"context": "Retrieved context"}
        assert result.error is None
        mock_rag.get_context.assert_called_once_with("test query", top_k=3)

    def test_execute_failure(self):
        """Test document retrieval failure"""
        mock_rag = Mock()
        mock_rag.get_context.side_effect = Exception("RAG error")
        
        tool = GetDocsTool(mock_rag)
        result = tool.execute(query="test")
        
        assert result.success is False
        assert result.data is None
        assert "RAG error" in result.error


class TestGetStateTool:
    """Test GetStateTool"""

    def test_tool_properties(self):
        """Test tool name and description"""
        mock_state = Mock()
        tool = GetStateTool(mock_state)
        
        assert tool.name == "get_state"
        assert isinstance(tool.description, str)

    def test_execute_success(self):
        """Test successful state retrieval"""
        mock_state = Mock()
        mock_state.get_sanitized_state.return_value = {
            "hosts": {"web": {"status": "running"}},
            "solved_flags": [],
        }
        
        tool = GetStateTool(mock_state)
        result = tool.execute()
        
        assert result.success is True
        assert "hosts" in result.data
        assert result.error is None

    def test_execute_failure(self):
        """Test state retrieval failure"""
        mock_state = Mock()
        mock_state.get_sanitized_state.side_effect = Exception("State error")
        
        tool = GetStateTool(mock_state)
        result = tool.execute()
        
        assert result.success is False
        assert "State error" in result.error


class TestValidateJSONTool:
    """Test ValidateJSONTool"""

    def test_tool_properties(self):
        """Test tool name and description"""
        mock_validator = Mock()
        tool = ValidateJSONTool(mock_validator)
        
        assert tool.name == "validate_json"
        assert isinstance(tool.description, str)

    def test_execute_valid_json(self):
        """Test validation of valid JSON"""
        mock_validator = Mock()
        mock_validator.validate.return_value = []  # No errors
        
        tool = ValidateJSONTool(mock_validator)
        result = tool.execute(json_str='{"key": "value"}')
        
        assert result.success is True
        assert "Valid JSON" in result.data["message"]

    def test_execute_invalid_json_syntax(self):
        """Test validation of invalid JSON syntax"""
        mock_validator = Mock()
        
        tool = ValidateJSONTool(mock_validator)
        result = tool.execute(json_str='{invalid json}')
        
        assert result.success is False
        assert "Invalid JSON" in result.error

    def test_execute_schema_errors(self):
        """Test validation with schema errors"""
        mock_validator = Mock()
        mock_validator.validate.return_value = ["Error 1", "Error 2"]
        
        tool = ValidateJSONTool(mock_validator)
        result = tool.execute(json_str='{"key": "value"}')
        
        assert result.success is False
        assert len(result.data["errors"]) == 2
        assert "Validation failed" in result.error


class TestDiffJSONTool:
    """Test DiffJSONTool"""

    def test_tool_properties(self):
        """Test tool name and description"""
        tool = DiffJSONTool()
        assert tool.name == "diff_json"
        assert isinstance(tool.description, str)

    def test_execute_no_differences(self):
        """Test diff with identical JSONs"""
        tool = DiffJSONTool()
        json1 = '{"key": "value"}'
        json2 = '{"key": "value"}'
        
        result = tool.execute(old_json=json1, new_json=json2)
        
        assert result.success is True
        assert len(result.data["diff"]) == 0

    def test_execute_value_changed(self):
        """Test diff with changed value"""
        tool = DiffJSONTool()
        json1 = '{"key": "old_value"}'
        json2 = '{"key": "new_value"}'
        
        result = tool.execute(old_json=json1, new_json=json2)
        
        assert result.success is True
        assert len(result.data["diff"]) == 1
        assert "key" in result.data["diff"][0]
        assert "old_value" in result.data["diff"][0]
        assert "new_value" in result.data["diff"][0]

    def test_execute_field_added(self):
        """Test diff with added field"""
        tool = DiffJSONTool()
        json1 = '{"key1": "value1"}'
        json2 = '{"key1": "value1", "key2": "value2"}'
        
        result = tool.execute(old_json=json1, new_json=json2)
        
        assert result.success is True
        diffs = result.data["diff"]
        assert any("added" in d for d in diffs)

    def test_execute_field_removed(self):
        """Test diff with removed field"""
        tool = DiffJSONTool()
        json1 = '{"key1": "value1", "key2": "value2"}'
        json2 = '{"key1": "value1"}'
        
        result = tool.execute(old_json=json1, new_json=json2)
        
        assert result.success is True
        diffs = result.data["diff"]
        assert any("removed" in d for d in diffs)

    def test_execute_nested_changes(self):
        """Test diff with nested object changes"""
        tool = DiffJSONTool()
        json1 = '{"outer": {"inner": "old"}}'
        json2 = '{"outer": {"inner": "new"}}'
        
        result = tool.execute(old_json=json1, new_json=json2)
        
        assert result.success is True
        assert len(result.data["diff"]) == 1
        assert "outer.inner" in result.data["diff"][0]

    def test_execute_list_length_change(self):
        """Test diff with list length change"""
        tool = DiffJSONTool()
        json1 = '{"list": [1, 2]}'
        json2 = '{"list": [1, 2, 3]}'
        
        result = tool.execute(old_json=json1, new_json=json2)
        
        assert result.success is True
        diffs = result.data["diff"]
        assert any("length changed" in d for d in diffs)

    def test_execute_invalid_json(self):
        """Test diff with invalid JSON"""
        tool = DiffJSONTool()
        
        result = tool.execute(old_json="{invalid}", new_json='{"valid": true}')
        
        assert result.success is False
        assert "Invalid JSON" in result.error


class TestToolRegistry:
    """Test ToolRegistry"""

    def test_registry_creation(self):
        """Test creating empty registry"""
        registry = ToolRegistry()
        assert len(registry.tools) == 0

    def test_register_tool(self):
        """Test registering a tool"""
        registry = ToolRegistry()
        mock_tool = Mock(spec=Tool)
        mock_tool.name = "test_tool"
        
        registry.register(mock_tool)
        
        assert "test_tool" in registry.tools
        assert registry.tools["test_tool"] == mock_tool

    def test_get_tool(self):
        """Test retrieving a tool"""
        registry = ToolRegistry()
        mock_tool = Mock(spec=Tool)
        mock_tool.name = "test_tool"
        registry.register(mock_tool)
        
        retrieved = registry.get_tool("test_tool")
        
        assert retrieved == mock_tool

    def test_get_nonexistent_tool(self):
        """Test retrieving nonexistent tool"""
        registry = ToolRegistry()
        retrieved = registry.get_tool("nonexistent")
        assert retrieved is None

    def test_execute_tool_success(self):
        """Test executing a tool successfully"""
        registry = ToolRegistry()
        mock_tool = Mock(spec=Tool)
        mock_tool.name = "test_tool"
        mock_tool.execute.return_value = ToolResult(success=True, data="result")
        registry.register(mock_tool)
        
        result = registry.execute_tool("test_tool", arg1="value1")
        
        assert result.success is True
        assert result.data == "result"
        mock_tool.execute.assert_called_once_with(arg1="value1")

    def test_execute_nonexistent_tool(self):
        """Test executing nonexistent tool"""
        registry = ToolRegistry()
        result = registry.execute_tool("nonexistent")
        
        assert result.success is False
        assert "not found" in result.error

    def test_list_tools(self):
        """Test listing all tools"""
        registry = ToolRegistry()
        
        mock_tool1 = Mock(spec=Tool)
        mock_tool1.name = "tool1"
        mock_tool1.description = "Description 1"
        
        mock_tool2 = Mock(spec=Tool)
        mock_tool2.name = "tool2"
        mock_tool2.description = "Description 2"
        
        registry.register(mock_tool1)
        registry.register(mock_tool2)
        
        tools = registry.list_tools()
        
        assert len(tools) == 2
        assert any(t["name"] == "tool1" for t in tools)
        assert any(t["name"] == "tool2" for t in tools)

    def test_get_tools_description(self):
        """Test getting formatted tool descriptions"""
        registry = ToolRegistry()
        
        mock_tool = Mock(spec=Tool)
        mock_tool.name = "test_tool"
        mock_tool.description = "Test description"
        registry.register(mock_tool)
        
        description = registry.get_tools_description()
        
        assert "AVAILABLE TOOLS" in description
        assert "test_tool" in description
        assert "Test description" in description


class TestCreateToolRegistry:
    """Test tool registry factory function"""

    def test_create_registry(self):
        """Test creating registry with all tools"""
        mock_rag = Mock()
        mock_state = Mock()
        mock_validator = Mock()
        
        registry = create_tool_registry(mock_rag, mock_state, mock_validator)
        
        assert isinstance(registry, ToolRegistry)
        assert len(registry.tools) == 4  # get_docs, get_state, validate_json, diff_json

    def test_created_registry_has_correct_tools(self):
        """Test that created registry has all expected tools"""
        mock_rag = Mock()
        mock_state = Mock()
        mock_validator = Mock()
        
        registry = create_tool_registry(mock_rag, mock_state, mock_validator)
        
        assert registry.get_tool("get_docs") is not None
        assert registry.get_tool("get_state") is not None
        assert registry.get_tool("validate_json") is not None
        assert registry.get_tool("diff_json") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
