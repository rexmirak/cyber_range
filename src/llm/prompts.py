"""
Prompts and prompt templates for LLM interactions

This module contains:
- System prompts for different LLM roles
- Prompt builders with chain-of-thought reasoning
- Few-shot examples for scenario authoring
"""

from typing import Dict, List, Any, Optional
import json


# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

SCENARIO_AUTHORING_SYSTEM = """You are an expert cybersecurity scenario designer for a cyber range platform.

Your role is to convert natural language descriptions into valid JSON scenario files.

CRITICAL RULES:
1. Output ONLY valid JSON - no explanations, no markdown, no comments
2. Use ONLY the enums provided - do not invent new values
3. Follow the JSON schema exactly - all required fields must be present
4. Be creative but realistic - vulnerabilities should be authentic
5. Ensure logical consistency (e.g., services match vulnerabilities)
6. Generate strong learning objectives
7. Create realistic network topologies
8. Place flags strategically based on objectives

OUTPUT FORMAT:
- Pure JSON only
- No ```json``` markers
- No prose before or after
- Properly escaped strings
- Valid syntax

If unsure, prefer simpler scenarios that are guaranteed to be valid."""

SCENARIO_REPAIR_SYSTEM = """You are a JSON repair specialist for cyber range scenarios.

Your role is to fix schema validation errors with MINIMAL changes.

CRITICAL RULES:
1. Make ONLY the changes necessary to fix the errors
2. Preserve user intent as much as possible
3. Do not add or remove major features unless required
4. Output ONLY valid JSON - no explanations
5. Use only allowed enum values
6. Ensure all references are valid (IDs must exist)
7. Fix syntax errors (quotes, commas, brackets)

REPAIR STRATEGY:
1. Read the error messages carefully
2. Identify the minimal fix
3. Apply the fix without altering other parts
4. Verify all references are correct
5. Output the complete, fixed JSON

OUTPUT FORMAT:
- Pure JSON only
- No explanations
- Complete scenario (not just the fixed part)"""

GUIDANCE_SYSTEM = """You are a helpful cybersecurity mentor guiding students through penetration testing labs.

Your role is to provide tiered hints without spoiling the learning experience.

CRITICAL RULES:
1. Never reveal flag values directly
2. Respect the hint tier level
3. Use only information from the provided scenario and lab state
4. Encourage independent thinking
5. Reference standard tools and techniques
6. Be encouraging and educational
7. If stuck, suggest methodology, not specific commands

HINT TIERS:
- Tier 0 (Nudge): Restate the objective, suggest starting point
- Tier 1 (Directional): Point to specific service or configuration area
- Tier 2 (Technique): Name the attack technique or tool
- Tier 3 (Detailed): Provide step-by-step guidance (but not exact commands)

TONE:
- Friendly and supportive
- Educational, not condescending
- Focus on learning, not just solving
- Relate to real-world scenarios

Always explain WHY something works, not just WHAT to do."""

EXPLAINER_SYSTEM = """You are a cybersecurity educator explaining concepts to students who just completed a lab.

Your role is to deepen understanding and connect practice to theory.

CRITICAL RULES:
1. Explain concepts clearly and thoroughly
2. Connect to the specific lab experience
3. Discuss real-world implications
4. Cover both offensive and defensive perspectives
5. Suggest remediation and best practices
6. Reference industry standards (OWASP, NIST, etc.)
7. Encourage further learning

STRUCTURE:
1. What: Define the concept clearly
2. Why: Explain why it's important
3. How: Describe how it works technically
4. Risk: Discuss real-world impact
5. Defense: Explain proper mitigations
6. Further: Suggest additional resources

TONE:
- Professional and educational
- Detailed but accessible
- Balanced (attack and defense)
- Encouraging continued growth"""


# ============================================================================
# PROMPT BUILDERS
# ============================================================================

def build_authoring_prompt(
    user_description: str,
    schema: Dict[str, Any],
    enums: Dict[str, List[str]],
    examples: Optional[List[Dict]] = None,
) -> str:
    """
    Build prompt for scenario authoring with chain-of-thought
    
    Args:
        user_description: User's natural language description
        schema: JSON schema
        enums: Available enum values
        examples: Few-shot examples
        
    Returns:
        Complete prompt
    """
    # Format enums for easy reference
    enum_section = "AVAILABLE ENUMS:\n"
    for key, values in enums.items():
        enum_section += f"- {key}: {', '.join(values)}\n"
    
    # Add few-shot examples if provided
    examples_section = ""
    if examples:
        examples_section = "\nEXAMPLE SCENARIOS:\n\n"
        for i, example in enumerate(examples[:2], 1):  # Limit to 2 examples
            examples_section += f"Example {i}:\n{json.dumps(example, indent=2)}\n\n"
    
    # Chain-of-thought reasoning template
    cot_template = """
REASONING STEPS (think through these, but only output JSON):
1. What is the main learning objective?
2. What vulnerabilities are needed?
3. What services host those vulnerabilities?
4. What network topology makes sense?
5. Where should flags be placed?
6. What difficulty level is appropriate?

Now, generate the complete scenario JSON:"""

    prompt = f"""USER DESCRIPTION:
{user_description}

{enum_section}

SCHEMA REQUIREMENTS:
- Must include: metadata, networks (min 1), hosts (min 1), flags (min 1)
- All IDs must be unique and follow pattern: ^[a-z][a-z0-9_]*$
- All references (network_id, service_id, etc.) must exist
- IP addresses must be valid and in subnet
- Resource limits: cpu_limit (e.g., "1.0"), memory_limit (e.g., "512m")

{examples_section}

{cot_template}
"""
    return prompt


def build_repair_prompt(
    broken_json: str,
    errors: List[str],
    schema: Dict[str, Any],
) -> str:
    """
    Build prompt for repairing invalid JSON
    
    Args:
        broken_json: The invalid JSON
        errors: Validation errors
        schema: JSON schema
        
    Returns:
        Complete prompt
    """
    errors_section = "VALIDATION ERRORS:\n"
    for i, error in enumerate(errors, 1):
        errors_section += f"{i}. {error}\n"
    
    prompt = f"""The following scenario JSON has validation errors:

{broken_json}

{errors_section}

TASK:
Fix ONLY the errors listed above. Make minimal changes.
Preserve the user's intent and all other parts of the scenario.

Output the complete, fixed JSON:"""
    
    return prompt


def build_hint_prompt(
    scenario: Dict[str, Any],
    lab_state: Dict[str, Any],
    tier: Any,  # HintTier enum
    user_question: Optional[str] = None,
) -> str:
    """
    Build prompt for generating hints
    
    Args:
        scenario: Scenario definition (sanitized)
        lab_state: Current lab state
        tier: Hint difficulty tier
        user_question: Optional user question
        
    Returns:
        Complete prompt
    """
    # Sanitize scenario (remove flag values)
    scenario_safe = _sanitize_scenario(scenario)
    
    tier_name = tier.name
    tier_instructions = {
        "NUDGE": "Give a gentle nudge. Restate the objective and suggest a starting methodology.",
        "DIRECTIONAL": "Point to the specific service or area to investigate. Don't name the attack yet.",
        "TECHNIQUE": "Name the specific attack technique or vulnerability type. Suggest appropriate tools.",
        "DETAILED": "Provide step-by-step guidance, but don't give exact commands. Explain the approach.",
    }
    
    question_section = ""
    if user_question:
        question_section = f"\n\nUSER QUESTION:\n{user_question}\n"
    
    prompt = f"""SCENARIO INFO:
Name: {scenario_safe.get('metadata', {}).get('name')}
Objectives: {', '.join(scenario_safe.get('narrative', {}).get('objectives', []))}

LAB STATE:
{json.dumps(lab_state, indent=2)}

{question_section}

HINT TIER: {tier_name} ({tier.value})
INSTRUCTIONS: {tier_instructions[tier_name]}

Provide a helpful hint at tier {tier.value}:"""
    
    return prompt


def build_explanation_prompt(
    topic: str,
    context: Dict[str, Any],
    event_log: Optional[List[Dict]] = None,
) -> str:
    """
    Build prompt for explaining concepts
    
    Args:
        topic: Topic to explain
        context: Relevant context
        event_log: Optional user action log
        
    Returns:
        Complete prompt
    """
    context_section = f"CONTEXT:\n{json.dumps(context, indent=2)}\n"
    
    log_section = ""
    if event_log:
        log_section = "\nUSER ACTIONS:\n"
        for event in event_log[-5:]:  # Last 5 actions
            log_section += f"- {event.get('action')}: {event.get('details')}\n"
    
    prompt = f"""TOPIC: {topic}

{context_section}

{log_section}

Provide a comprehensive explanation of this topic:
1. Definition and overview
2. How it relates to the lab they just completed
3. Technical details
4. Real-world security implications
5. Proper defenses and mitigations
6. Resources for further learning

Explanation:"""
    
    return prompt


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _sanitize_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove sensitive data (flag values) from scenario
    
    Args:
        scenario: Full scenario
        
    Returns:
        Sanitized scenario
    """
    import copy
    safe = copy.deepcopy(scenario)
    
    # Replace flag values with placeholders
    if "flags" in safe:
        for flag in safe["flags"]:
            if "value" in flag:
                flag["value"] = "[REDACTED]"
    
    return safe


# ============================================================================
# FEW-SHOT EXAMPLES
# ============================================================================

FEW_SHOT_EXAMPLES = [
    {
        "description": "Simple web server with SQL injection",
        "scenario": {
            "metadata": {
                "name": "Basic SQLi Challenge",
                "description": "Learn SQL injection basics",
                "author": "CyberRange",
                "version": "1.0.0",
                "difficulty": "easy",
                "estimated_time_minutes": 30,
                "tags": ["web", "sqli"],
                "learning_objectives": ["Identify SQL injection", "Extract data"]
            },
            "networks": [
                {
                    "id": "net_main",
                    "name": "main",
                    "type": "custom_bridge",
                    "subnet": "172.20.0.0/16"
                }
            ],
            "hosts": [
                {
                    "id": "host_attacker",
                    "name": "attacker",
                    "type": "attacker",
                    "base_image": "kalilinux/kali-rolling",
                    "networks": [{"network_id": "net_main", "ip_address": "172.20.0.10"}],
                    "resources": {"cpu_limit": "1.0", "memory_limit": "1g"},
                    "services": [],
                    "vulnerabilities": [],
                    "flags": []
                },
                {
                    "id": "host_web",
                    "name": "webserver",
                    "type": "web",
                    "base_image": "php:7.4-apache",
                    "networks": [{"network_id": "net_main", "ip_address": "172.20.0.20"}],
                    "resources": {"cpu_limit": "0.5", "memory_limit": "512m"},
                    "services": ["svc_web"],
                    "vulnerabilities": ["vuln_sqli"],
                    "flags": ["flag_password"]
                }
            ],
            "services": [
                {
                    "id": "svc_web",
                    "name": "web_app",
                    "type": "apache",
                    "version": "2.4",
                    "ports": [{"internal": 80, "protocol": "tcp"}],
                    "config": {"credentials": [{"username": "admin", "password": "secret"}]}
                }
            ],
            "vulnerabilities": [
                {
                    "id": "vuln_sqli",
                    "name": "SQL Injection",
                    "type": "sql_injection",
                    "severity": "high",
                    "description": "Login form vulnerable to SQLi",
                    "affected_service": "svc_web",
                    "setup": {"module": "modules/sqli_login.sh", "parameters": {}}
                }
            ],
            "flags": [
                {
                    "id": "flag_password",
                    "name": "Admin Password",
                    "value": "FLAG{sql_injection_success}",
                    "placement": {
                        "type": "db_row",
                        "host_id": "host_web",
                        "details": {"table": "users", "query": "SELECT password FROM users"}
                    },
                    "points": 100
                }
            ],
            "scoring": {"total_points": 100, "passing_score": 100, "time_bonus": False, "penalty_for_hints": False},
            "narrative": {
                "scenario_background": "Test a web application for SQL injection",
                "attacker_role": "Pentester",
                "objectives": ["Find SQLi", "Extract password"],
                "success_criteria": "Capture the flag"
            }
        }
    }
]


def get_few_shot_examples() -> List[Dict]:
    """Get curated few-shot examples for scenario authoring"""
    return FEW_SHOT_EXAMPLES
