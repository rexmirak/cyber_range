"""
Unit tests for Prompts Module

Tests prompt builders and templates.
"""

import pytest
import json

from src.llm.prompts import (
    build_authoring_prompt,
    build_repair_prompt,
    build_hint_prompt,
    build_explanation_prompt,
    get_few_shot_examples,
    _sanitize_scenario,
    SCENARIO_AUTHORING_SYSTEM,
    SCENARIO_REPAIR_SYSTEM,
    GUIDANCE_SYSTEM,
    EXPLAINER_SYSTEM,
)
from src.llm.adapter import HintTier


class TestSystemPrompts:
    """Test system prompt constants"""

    def test_authoring_system_prompt_exists(self):
        """Test scenario authoring system prompt"""
        assert isinstance(SCENARIO_AUTHORING_SYSTEM, str)
        assert len(SCENARIO_AUTHORING_SYSTEM) > 100
        assert "JSON" in SCENARIO_AUTHORING_SYSTEM
        assert "enum" in SCENARIO_AUTHORING_SYSTEM.lower()

    def test_repair_system_prompt_exists(self):
        """Test repair system prompt"""
        assert isinstance(SCENARIO_REPAIR_SYSTEM, str)
        assert len(SCENARIO_REPAIR_SYSTEM) > 50
        assert "MINIMAL" in SCENARIO_REPAIR_SYSTEM
        assert "fix" in SCENARIO_REPAIR_SYSTEM.lower()

    def test_guidance_system_prompt_exists(self):
        """Test guidance system prompt"""
        assert isinstance(GUIDANCE_SYSTEM, str)
        assert len(GUIDANCE_SYSTEM) > 100
        assert "hint" in GUIDANCE_SYSTEM.lower()
        assert "tier" in GUIDANCE_SYSTEM.lower()

    def test_explainer_system_prompt_exists(self):
        """Test explainer system prompt"""
        assert isinstance(EXPLAINER_SYSTEM, str)
        assert len(EXPLAINER_SYSTEM) > 100
        assert "explain" in EXPLAINER_SYSTEM.lower()
        assert "concept" in EXPLAINER_SYSTEM.lower()


class TestBuildAuthoringPrompt:
    """Test authoring prompt builder"""

    def test_basic_prompt_structure(self):
        """Test basic prompt structure"""
        prompt = build_authoring_prompt(
            user_description="Create a simple web lab",
            schema={},
            enums={"difficulty": ["easy", "medium", "hard"]},
        )
        
        assert isinstance(prompt, str)
        assert "Create a simple web lab" in prompt
        assert "AVAILABLE ENUMS:" in prompt
        assert "difficulty" in prompt

    def test_prompt_includes_enums(self):
        """Test that prompt includes all enums"""
        enums = {
            "difficulty": ["easy", "medium", "hard"],
            "host_type": ["attacker", "victim", "web"],
        }
        
        prompt = build_authoring_prompt(
            user_description="Test",
            schema={},
            enums=enums,
        )
        
        assert "difficulty" in prompt
        assert "host_type" in prompt
        assert "easy" in prompt
        assert "attacker" in prompt

    def test_prompt_with_examples(self):
        """Test prompt includes few-shot examples"""
        examples = [{"metadata": {"name": "Example"}}]
        
        prompt = build_authoring_prompt(
            user_description="Test",
            schema={},
            enums={},
            examples=examples,
        )
        
        assert "EXAMPLE SCENARIOS:" in prompt
        assert "Example" in prompt

    def test_prompt_without_examples(self):
        """Test prompt without examples"""
        prompt = build_authoring_prompt(
            user_description="Test",
            schema={},
            enums={},
            examples=None,
        )
        
        assert "EXAMPLE SCENARIOS:" not in prompt

    def test_prompt_includes_cot(self):
        """Test prompt includes chain-of-thought"""
        prompt = build_authoring_prompt(
            user_description="Test",
            schema={},
            enums={},
        )
        
        assert "REASONING STEPS" in prompt
        assert "learning objective" in prompt


class TestBuildRepairPrompt:
    """Test repair prompt builder"""

    def test_basic_repair_prompt(self):
        """Test basic repair prompt structure"""
        broken_json = '{"metadata": {}}'
        errors = ["Missing required field: name"]
        
        prompt = build_repair_prompt(
            broken_json=broken_json,
            errors=errors,
            schema={},
        )
        
        assert isinstance(prompt, str)
        assert broken_json in prompt
        assert "Missing required field: name" in prompt

    def test_multiple_errors(self):
        """Test prompt with multiple errors"""
        errors = ["Error 1", "Error 2", "Error 3"]
        
        prompt = build_repair_prompt(
            broken_json="{}",
            errors=errors,
            schema={},
        )
        
        assert all(error in prompt for error in errors)

    def test_repair_instructions(self):
        """Test repair prompt includes instructions"""
        prompt = build_repair_prompt(
            broken_json="{}",
            errors=["Error"],
            schema={},
        )
        
        assert "Fix ONLY" in prompt or "fix" in prompt.lower()
        assert "minimal" in prompt.lower()


class TestBuildHintPrompt:
    """Test hint prompt builder"""

    def test_basic_hint_prompt(self):
        """Test basic hint prompt structure"""
        scenario = {
            "metadata": {"name": "Test Lab"},
            "narrative": {"objectives": ["Objective 1"]},
        }
        lab_state = {"hosts": {}, "solved_flags": []}
        
        prompt = build_hint_prompt(
            scenario=scenario,
            lab_state=lab_state,
            tier=HintTier.NUDGE,
        )
        
        assert isinstance(prompt, str)
        assert "Test Lab" in prompt
        assert "Objective 1" in prompt

    def test_hint_tiers(self):
        """Test different hint tiers"""
        scenario = {"metadata": {"name": "Lab"}, "narrative": {"objectives": []}}
        lab_state = {}
        
        for tier in [HintTier.NUDGE, HintTier.DIRECTIONAL, HintTier.TECHNIQUE, HintTier.DETAILED]:
            prompt = build_hint_prompt(scenario, lab_state, tier)
            assert tier.name in prompt
            assert str(tier.value) in prompt

    def test_hint_with_user_question(self):
        """Test hint prompt with user question"""
        scenario = {"metadata": {"name": "Lab"}, "narrative": {"objectives": []}}
        lab_state = {}
        user_question = "How do I bypass the login?"
        
        prompt = build_hint_prompt(
            scenario=scenario,
            lab_state=lab_state,
            tier=HintTier.TECHNIQUE,
            user_question=user_question,
        )
        
        assert user_question in prompt

    def test_flag_sanitization(self):
        """Test that flag values are redacted"""
        scenario = {
            "metadata": {"name": "Lab"},
            "narrative": {"objectives": []},
            "flags": [
                {"id": "flag1", "value": "SECRET_FLAG_VALUE"}
            ]
        }
        lab_state = {}
        
        prompt = build_hint_prompt(scenario, lab_state, HintTier.NUDGE)
        
        # Flag value should be redacted
        assert "SECRET_FLAG_VALUE" not in prompt or "[REDACTED]" in prompt


class TestBuildExplanationPrompt:
    """Test explanation prompt builder"""

    def test_basic_explanation_prompt(self):
        """Test basic explanation prompt"""
        prompt = build_explanation_prompt(
            topic="SQL Injection",
            context={"scenario": {"name": "Test"}},
        )
        
        assert isinstance(prompt, str)
        assert "SQL Injection" in prompt

    def test_explanation_with_event_log(self):
        """Test explanation with event log"""
        event_log = [
            {"action": "scan", "details": "Found web server"},
            {"action": "exploit", "details": "Attempted SQLi"},
        ]
        
        prompt = build_explanation_prompt(
            topic="SQL Injection",
            context={},
            event_log=event_log,
        )
        
        assert "scan" in prompt
        assert "exploit" in prompt

    def test_explanation_limits_event_log(self):
        """Test that event log is limited to recent events"""
        event_log = [{"action": f"action_{i}", "details": f"detail_{i}"} for i in range(10)]
        
        prompt = build_explanation_prompt(
            topic="Test",
            context={},
            event_log=event_log,
        )
        
        # Should only include last 5
        assert "action_9" in prompt
        assert "action_5" in prompt
        assert "action_0" not in prompt


class TestSanitizeScenario:
    """Test scenario sanitization"""

    def test_sanitize_removes_flag_values(self):
        """Test that flag values are redacted"""
        scenario = {
            "flags": [
                {"id": "flag1", "value": "SECRET_VALUE_1"},
                {"id": "flag2", "value": "SECRET_VALUE_2"},
            ]
        }
        
        sanitized = _sanitize_scenario(scenario)
        
        assert sanitized["flags"][0]["value"] == "[REDACTED]"
        assert sanitized["flags"][1]["value"] == "[REDACTED]"
        assert "SECRET_VALUE_1" not in json.dumps(sanitized)

    def test_sanitize_preserves_other_data(self):
        """Test that other data is preserved"""
        scenario = {
            "metadata": {"name": "Test Lab"},
            "flags": [{"id": "flag1", "value": "SECRET", "name": "Flag Name"}],
        }
        
        sanitized = _sanitize_scenario(scenario)
        
        assert sanitized["metadata"]["name"] == "Test Lab"
        assert sanitized["flags"][0]["name"] == "Flag Name"
        assert sanitized["flags"][0]["id"] == "flag1"

    def test_sanitize_no_flags(self):
        """Test sanitization with no flags"""
        scenario = {"metadata": {"name": "Test"}}
        sanitized = _sanitize_scenario(scenario)
        assert sanitized == scenario

    def test_sanitize_doesnt_modify_original(self):
        """Test that original scenario is not modified"""
        scenario = {
            "flags": [{"id": "flag1", "value": "SECRET"}]
        }
        
        sanitized = _sanitize_scenario(scenario)
        
        # Original should be unchanged
        assert scenario["flags"][0]["value"] == "SECRET"
        # Sanitized should be redacted
        assert sanitized["flags"][0]["value"] == "[REDACTED]"


class TestFewShotExamples:
    """Test few-shot examples"""

    def test_get_few_shot_examples(self):
        """Test retrieving few-shot examples"""
        examples = get_few_shot_examples()
        
        assert isinstance(examples, list)
        assert len(examples) > 0

    def test_few_shot_example_structure(self):
        """Test few-shot example has correct structure"""
        examples = get_few_shot_examples()
        
        for example in examples:
            assert "description" in example
            assert "scenario" in example
            assert isinstance(example["scenario"], dict)

    def test_few_shot_scenario_valid(self):
        """Test that few-shot scenarios have required fields"""
        examples = get_few_shot_examples()
        
        for example in examples:
            scenario = example["scenario"]
            assert "metadata" in scenario
            assert "networks" in scenario
            assert "hosts" in scenario
            assert "flags" in scenario


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
