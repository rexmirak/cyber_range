"""
Ollama LLM Adapter for Cyber Range Scenario Deployer

This module provides a clean interface to Ollama for:
- Scenario authoring (JSON generation from natural language)
- Scenario repair (fixing schema violations)
- In-lab guidance (tiered hints)
- Learning explanations
"""

import json
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class HintTier(Enum):
    """Hint difficulty tiers"""
    NUDGE = 0  # Gentle reminder of objective
    DIRECTIONAL = 1  # Suggest area or service
    TECHNIQUE = 2  # Specific attack method
    DETAILED = 3  # Step-by-step walkthrough


@dataclass
class LLMConfig:
    """Configuration for Ollama LLM"""
    base_url: str = "http://localhost:11434"
    model: str = "llama3.2:latest"
    temperature: float = 0.2  # Low for deterministic output
    timeout: int = 120


class OllamaAdapter:
    """Adapter for Ollama local LLM"""

    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
        self._verify_connection()

    def _verify_connection(self) -> None:
        """Verify Ollama is running and model is available"""
        try:
            response = requests.get(f"{self.config.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            models = response.json().get("models", [])
            
            if not any(m.get("name") == self.config.model for m in models):
                raise RuntimeError(
                    f"Model {self.config.model} not found. "
                    f"Run: ollama pull {self.config.model}"
                )
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.config.base_url}. "
                "Is Ollama running? Start it with: ollama serve"
            )

    def _generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
    ) -> str:
        """
        Generate completion from Ollama
        
        Args:
            prompt: User prompt
            system: System message (instructions)
            temperature: Sampling temperature (0.0-1.0)
            stream: Whether to stream response
            
        Returns:
            Generated text
        """
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature or self.config.temperature,
            }
        }
        
        if system:
            payload["system"] = system

        try:
            response = requests.post(
                f"{self.config.base_url}/api/generate",
                json=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            
            if stream:
                # Handle streaming responses
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        full_response += chunk.get("response", "")
                return full_response
            else:
                return response.json()["response"]
                
        except requests.exceptions.Timeout:
            raise RuntimeError(f"LLM request timed out after {self.config.timeout}s")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"LLM request failed: {e}")

    def generate_scenario_json(
        self,
        user_description: str,
        schema: Dict[str, Any],
        enums: Dict[str, List[str]],
        examples: Optional[List[Dict]] = None,
    ) -> str:
        """
        Generate scenario JSON from natural language description
        
        Args:
            user_description: Natural language scenario description
            schema: JSON schema definition
            enums: Available enum values
            examples: Example scenarios for few-shot learning
            
        Returns:
            Generated JSON as string
        """
        from .prompts import SCENARIO_AUTHORING_SYSTEM, build_authoring_prompt
        
        prompt = build_authoring_prompt(
            user_description=user_description,
            schema=schema,
            enums=enums,
            examples=examples,
        )
        
        # Use lower temperature for more deterministic JSON
        response = self._generate(
            prompt=prompt,
            system=SCENARIO_AUTHORING_SYSTEM,
            temperature=0.1,
        )
        
        # Extract JSON from response (handle markdown code blocks)
        return self._extract_json(response)

    def repair_scenario_json(
        self,
        broken_json: str,
        errors: List[str],
        schema: Dict[str, Any],
    ) -> str:
        """
        Repair invalid scenario JSON
        
        Args:
            broken_json: The invalid JSON
            errors: List of validation errors
            schema: JSON schema for reference
            
        Returns:
            Repaired JSON as string
        """
        from .prompts import SCENARIO_REPAIR_SYSTEM, build_repair_prompt
        
        prompt = build_repair_prompt(
            broken_json=broken_json,
            errors=errors,
            schema=schema,
        )
        
        response = self._generate(
            prompt=prompt,
            system=SCENARIO_REPAIR_SYSTEM,
            temperature=0.1,
        )
        
        return self._extract_json(response)

    def suggest_hint(
        self,
        scenario: Dict[str, Any],
        lab_state: Dict[str, Any],
        tier: HintTier,
        user_question: Optional[str] = None,
    ) -> str:
        """
        Generate a hint for the user
        
        Args:
            scenario: The scenario definition
            lab_state: Current lab state (sanitized)
            tier: Hint difficulty tier
            user_question: Optional specific question from user
            
        Returns:
            Hint text
        """
        from .prompts import GUIDANCE_SYSTEM, build_hint_prompt
        
        prompt = build_hint_prompt(
            scenario=scenario,
            lab_state=lab_state,
            tier=tier,
            user_question=user_question,
        )
        
        # Use moderate temperature for more creative hints
        return self._generate(
            prompt=prompt,
            system=GUIDANCE_SYSTEM,
            temperature=0.4,
        )

    def explain_concept(
        self,
        topic: str,
        context: Dict[str, Any],
        event_log: Optional[List[Dict]] = None,
    ) -> str:
        """
        Explain a security concept or technique
        
        Args:
            topic: Topic to explain
            context: Relevant context (scenario, vulnerabilities, etc.)
            event_log: Optional log of user actions
            
        Returns:
            Explanation text
        """
        from .prompts import EXPLAINER_SYSTEM, build_explanation_prompt
        
        prompt = build_explanation_prompt(
            topic=topic,
            context=context,
            event_log=event_log,
        )
        
        return self._generate(
            prompt=prompt,
            system=EXPLAINER_SYSTEM,
            temperature=0.3,
        )

    def _extract_json(self, response: str) -> str:
        """
        Extract JSON from LLM response, handling markdown code blocks
        
        Args:
            response: Raw LLM response
            
        Returns:
            Clean JSON string
        """
        # Remove markdown code blocks if present
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()
        
        # Validate it's actually JSON
        try:
            json.loads(response)
            return response
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM did not return valid JSON: {e}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        """
        Multi-turn chat conversation
        
        Args:
            messages: List of {role, content} messages
            system: System message
            temperature: Sampling temperature
            
        Returns:
            Assistant response
        """
        # Build context from previous messages
        context = "\n\n".join([
            f"{m['role'].upper()}: {m['content']}"
            for m in messages[:-1]
        ])
        
        current_prompt = messages[-1]["content"]
        
        if context:
            full_prompt = f"{context}\n\nUSER: {current_prompt}\n\nASSISTANT:"
        else:
            full_prompt = current_prompt
        
        return self._generate(
            prompt=full_prompt,
            system=system,
            temperature=temperature,
        )
