"""
LLM Integration Module

High-level interface combining adapter, prompts, RAG, and tools.
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import json

from .adapter import OllamaAdapter, HintTier, LLMConfig
from .rag import LocalRAG
from .tools import ToolRegistry, create_tool_registry
from .prompts import get_few_shot_examples


class LLMIntegration:
    """
    High-level LLM integration for cyber range
    
    Combines:
    - Ollama adapter for generation
    - RAG pipeline for context
    - Tool registry for safe operations
    - Prompt templates and few-shot examples
    """

    def __init__(
        self,
        llm_config: Optional[LLMConfig] = None,
        rag_db_path: str = ".cyber_range/rag.db",
        enable_rag: bool = True,
    ):
        """
        Initialize LLM integration
        
        Args:
            llm_config: LLM configuration
            rag_db_path: Path to RAG database
            enable_rag: Whether to enable RAG pipeline
        """
        self.llm = OllamaAdapter(llm_config)
        self.rag = LocalRAG(rag_db_path) if enable_rag else None
        self.tools: Optional[ToolRegistry] = None

    def setup_tools(self, state_manager, validator) -> None:
        """
        Setup tool registry
        
        Args:
            state_manager: Lab state manager
            validator: JSON validator
        """
        if self.rag:
            self.tools = create_tool_registry(self.rag, state_manager, validator)
        else:
            raise RuntimeError("RAG pipeline must be enabled to use tools")

    def author_scenario(
        self,
        user_description: str,
        schema: Dict[str, Any],
        enums: Dict[str, List[str]],
        use_few_shot: bool = True,
    ) -> Dict[str, Any]:
        """
        Author a scenario from natural language description
        
        Args:
            user_description: User's description
            schema: JSON schema
            enums: Available enums
            use_few_shot: Whether to include few-shot examples
            
        Returns:
            Generated scenario JSON
        """
        examples = get_few_shot_examples() if use_few_shot else None
        
        # Enhance description with RAG context if available
        if self.rag:
            related_docs = self.rag.get_context(
                user_description,
                top_k=2,
                max_chars=500
            )
            if related_docs:
                user_description = f"{user_description}\n\nRELATED EXAMPLES:\n{related_docs}"
        
        json_str = self.llm.generate_scenario_json(
            user_description=user_description,
            schema=schema,
            enums=enums,
            examples=examples,
        )
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Return raw structure hint if decode fails
            return {"_raw": json_str, "_error": "decode_failed"}

    def repair_scenario(
        self,
        broken_json: str,
        errors: List[str],
        schema: Dict[str, Any],
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """
        Repair invalid scenario JSON with retry logic
        
        Args:
            broken_json: Invalid JSON
            errors: Validation errors
            schema: JSON schema
            max_attempts: Maximum repair attempts
            
        Returns:
            Repaired scenario JSON
            
        Raises:
            ValueError: If repair fails after max_attempts
        """
        for attempt in range(max_attempts):
            try:
                repaired_str = self.llm.repair_scenario_json(
                    broken_json=broken_json,
                    errors=errors,
                    schema=schema,
                )
                try:
                    return json.loads(repaired_str)
                except json.JSONDecodeError as de:
                    raise ValueError(f"Repaired JSON decode failure: {de}")
            except (json.JSONDecodeError, ValueError) as e:
                if attempt == max_attempts - 1:
                    raise ValueError(
                        f"Failed to repair JSON after {max_attempts} attempts: {e}"
                    )
                errors.append(f"Attempt {attempt + 1} failed: {e}")
        # Fallback - should not reach here due to return or raise in loop
        raise ValueError("Repair attempts exhausted without return")

    def provide_hint(
        self,
        scenario: Dict[str, Any],
        lab_state: Dict[str, Any],
        tier: HintTier,
        user_question: Optional[str] = None,
    ) -> str:
        """
        Provide a hint to the user
        
        Args:
            scenario: Scenario definition
            lab_state: Current lab state
            tier: Hint difficulty tier
            user_question: Optional user question
            
        Returns:
            Hint text
        """
        # Enhance with RAG context if available
        context_query = user_question or "hint guidance help"
        if self.rag:
            rag_context = self.rag.get_context(context_query, top_k=1, max_chars=300)
            if rag_context:
                lab_state["_rag_context"] = rag_context
        
        return self.llm.suggest_hint(
            scenario=scenario,
            lab_state=lab_state,
            tier=tier,
            user_question=user_question,
        )

    def explain_topic(
        self,
        topic: str,
        scenario: Dict[str, Any],
        event_log: Optional[List[Dict]] = None,
    ) -> str:
        """
        Explain a security topic or concept
        
        Args:
            topic: Topic to explain
            scenario: Scenario context
            event_log: Optional user action log
            
        Returns:
            Explanation text
        """
        # Enhance with RAG context
        context: Dict[str, Any] = {"scenario": scenario}
        if self.rag:
            rag_context = self.rag.get_context(topic, top_k=2, max_chars=800)
            if rag_context:
                context["documentation"] = rag_context
        
        return self.llm.explain_concept(
            topic=topic,
            context=context,
            event_log=event_log,
        )

    def index_scenario(self, scenario: Dict[str, Any]) -> List[str]:
        """
        Index a scenario in RAG pipeline
        
        Args:
            scenario: Scenario to index
            
        Returns:
            List of indexed document IDs
        """
        if not self.rag:
            raise RuntimeError("RAG pipeline not enabled")
        return self.rag.index_scenario(scenario)

    def index_knowledge_base(self, kb_dir: Path) -> int:
        """
        Index knowledge base documents
        
        Args:
            kb_dir: Knowledge base directory
            
        Returns:
            Number of documents indexed
        """
        if not self.rag:
            raise RuntimeError("RAG pipeline not enabled")
        return self.rag.index_knowledge_base(kb_dir)

    def interactive_authoring(
        self,
        schema: Dict[str, Any],
        enums: Dict[str, List[str]],
        validator,
    ) -> Optional[Dict[str, Any]]:
        """
        Interactive authoring session with repair loop
        
        Args:
            schema: JSON schema
            enums: Available enums
            validator: JSON validator
            
        Returns:
            Valid scenario JSON or None
        """
        print("🤖 Scenario Authoring Assistant")
        print("Describe the scenario you want to create:")
        print()
        
        user_input = input("> ")
        print("\n🔨 Generating scenario...")
        
        # Generate initial scenario
        try:
            scenario = self.author_scenario(user_input, schema, enums)
        except Exception as e:
            print(f"❌ Generation failed: {e}")
            return None
        
        # Validate and repair loop
        max_iterations = 3
        for iteration in range(max_iterations):
            vres = validator.validate(scenario)
            if vres.is_valid:
                print("✅ Valid scenario generated!")
                return scenario
            print(
                f"⚠️  Found {len(vres.errors)} validation errors. Attempting repair..."
            )
            try:
                scenario_str = json.dumps(scenario, indent=2)
                scenario = self.repair_scenario(
                    scenario_str,
                    [str(e) for e in vres.errors],
                    schema,
                )
            except Exception as e:
                print(f"❌ Repair failed: {e}")
                if iteration == max_iterations - 1:
                    print(
                        "💡 Try simplifying your description or being more specific."
                    )
                    return None
        
        print("❌ Could not generate valid scenario after multiple attempts")
        return None

    def chat_session(
        self,
        scenario: Dict[str, Any],
        lab_state: Dict[str, Any],
    ) -> None:
        """
        Interactive chat session for guidance
        
        Args:
            scenario: Current scenario
            lab_state: Current lab state
        """
        print("💬 Lab Guidance Chat")
        print("Ask questions or type 'hint' for suggestions (type 'exit' to quit)")
        print()
        
        messages = []
        hint_tier = HintTier.NUDGE
        
        while True:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ["exit", "quit", "q"]:
                break
            
            if user_input.lower() == "hint":
                response = self.provide_hint(scenario, lab_state, hint_tier)
                # Increase hint tier for next time
                if hint_tier.value < HintTier.DETAILED.value:
                    hint_tier = HintTier(hint_tier.value + 1)
            else:
                # General question
                messages.append({"role": "user", "content": user_input})
                response = self.llm.chat(messages, system=None)
                messages.append({"role": "assistant", "content": response})
            
            print(f"\n🤖 Assistant: {response}\n")
