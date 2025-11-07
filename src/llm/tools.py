"""
Tool Interface for LLM

Provides safe, limited tools that the LLM can use to gather context
without directly executing commands or modifying state.
"""

from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass
import json


@dataclass
class ToolResult:
    """Result from a tool execution"""
    success: bool
    data: Any
    error: Optional[str] = None


class Tool(ABC):
    """Base class for LLM tools"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        pass


class GetDocsTool(Tool):
    """Retrieve documentation chunks"""

    def __init__(self, rag_pipeline):
        self.rag = rag_pipeline

    @property
    def name(self) -> str:
        return "get_docs"

    @property
    def description(self) -> str:
        return "Retrieve relevant documentation for a query. Args: query (str), top_k (int, optional)"

    def execute(self, query: str, top_k: int = 3, **kwargs) -> ToolResult:
        """
        Retrieve documentation
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            ToolResult with documents
        """
        try:
            context = self.rag.get_context(query, top_k=top_k)
            return ToolResult(success=True, data={"context": context})
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))


class GetStateTool(Tool):
    """Retrieve current lab state"""

    def __init__(self, state_manager):
        self.state = state_manager

    @property
    def name(self) -> str:
        return "get_state"

    @property
    def description(self) -> str:
        return "Get sanitized snapshot of current lab state (hosts, services, health, solved flags)"

    def execute(self, **kwargs) -> ToolResult:
        """
        Get lab state
        
        Returns:
            ToolResult with sanitized state
        """
        try:
            state = self.state.get_sanitized_state()
            return ToolResult(success=True, data=state)
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))


class ValidateJSONTool(Tool):
    """Validate scenario JSON against schema"""

    def __init__(self, validator):
        self.validator = validator

    @property
    def name(self) -> str:
        return "validate_json"

    @property
    def description(self) -> str:
        return "Validate scenario JSON. Args: json_str (str)"

    def execute(self, json_str: str, **kwargs) -> ToolResult:
        """
        Validate JSON
        
        Args:
            json_str: JSON string to validate
            
        Returns:
            ToolResult with validation results
        """
        try:
            scenario = json.loads(json_str)
            errors = self.validator.validate(scenario)
            
            if errors:
                return ToolResult(
                    success=False,
                    data={"errors": errors},
                    error=f"Validation failed with {len(errors)} errors"
                )
            else:
                return ToolResult(success=True, data={"message": "Valid JSON"})
        except json.JSONDecodeError as e:
            return ToolResult(success=False, data=None, error=f"Invalid JSON: {e}")
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))


class DiffJSONTool(Tool):
    """Compare two JSON scenarios"""

    @property
    def name(self) -> str:
        return "diff_json"

    @property
    def description(self) -> str:
        return "Compare two scenario JSONs. Args: old_json (str), new_json (str)"

    def execute(self, old_json: str, new_json: str, **kwargs) -> ToolResult:
        """
        Compute diff between two JSONs
        
        Args:
            old_json: Original JSON
            new_json: Modified JSON
            
        Returns:
            ToolResult with structured diff
        """
        try:
            old = json.loads(old_json)
            new = json.loads(new_json)
            
            diff = self._compute_diff(old, new)
            return ToolResult(success=True, data={"diff": diff})
        except json.JSONDecodeError as e:
            return ToolResult(success=False, data=None, error=f"Invalid JSON: {e}")
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    def _compute_diff(self, old: Any, new: Any, path: str = "") -> List[str]:
        """Recursively compute differences"""
        diffs = []
        
        if type(old) != type(new):
            diffs.append(f"{path}: type changed from {type(old).__name__} to {type(new).__name__}")
            return diffs
        
        if isinstance(old, dict):
            all_keys = set(old.keys()) | set(new.keys())
            for key in all_keys:
                new_path = f"{path}.{key}" if path else key
                if key not in old:
                    diffs.append(f"{new_path}: added")
                elif key not in new:
                    diffs.append(f"{new_path}: removed")
                else:
                    diffs.extend(self._compute_diff(old[key], new[key], new_path))
        elif isinstance(old, list):
            if len(old) != len(new):
                diffs.append(f"{path}: list length changed from {len(old)} to {len(new)}")
            for i, (old_item, new_item) in enumerate(zip(old, new)):
                diffs.extend(self._compute_diff(old_item, new_item, f"{path}[{i}]"))
        else:
            if old != new:
                diffs.append(f"{path}: changed from '{old}' to '{new}'")
        
        return diffs


class ToolRegistry:
    """Registry of available tools for LLM"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool"""
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name"""
        return self.tools.get(name)

    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name"""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                data=None,
                error=f"Tool '{name}' not found"
            )
        return tool.execute(**kwargs)

    def list_tools(self) -> List[Dict[str, str]]:
        """List all available tools"""
        return [
            {"name": tool.name, "description": tool.description}
            for tool in self.tools.values()
        ]

    def get_tools_description(self) -> str:
        """Get formatted description of all tools"""
        descriptions = ["AVAILABLE TOOLS:"]
        for tool in self.tools.values():
            descriptions.append(f"- {tool.name}: {tool.description}")
        return "\n".join(descriptions)


def create_tool_registry(rag_pipeline, state_manager, validator) -> ToolRegistry:
    """
    Create and populate tool registry
    
    Args:
        rag_pipeline: RAG pipeline instance
        state_manager: State manager instance
        validator: JSON validator instance
        
    Returns:
        Configured ToolRegistry
    """
    registry = ToolRegistry()
    
    registry.register(GetDocsTool(rag_pipeline))
    registry.register(GetStateTool(state_manager))
    registry.register(ValidateJSONTool(validator))
    registry.register(DiffJSONTool())
    
    return registry
