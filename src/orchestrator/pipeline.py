"""
Orchestrator pipeline: validate then plan

This module glues together the validator and planner to produce a safe
deployment plan only when the scenario is valid.
"""
from typing import Optional, Tuple

from src.validator.scenario_validator import ScenarioValidator, ValidationResult
from src.planner.planner import plan_scenario, PlanResult


def validate_and_plan(scenario: dict) -> Tuple[ValidationResult, Optional[PlanResult]]:
    """
    Validate a scenario and, if valid, produce a plan.

    Returns a tuple of (validation_result, plan_result_or_None).
    If validation fails, the plan result will be None.
    """
    validator = ScenarioValidator()
    validation = validator.validate(scenario)
    if not validation.is_valid:
        return validation, None
    plan = plan_scenario(scenario)
    return validation, plan
