"""
Example: Using the LLM Integration Module

This script demonstrates how to use the LLM features:
1. Scenario authoring from natural language
2. Automatic repair of invalid JSON
3. In-lab guidance and hints
4. Concept explanations
"""

import json
from pathlib import Path

from src.llm import OllamaAdapter, LLMConfig, HintTier
from src.llm.integration import LLMIntegration


def example_1_simple_generation():
    """Example: Generate a simple scenario"""
    print("=" * 60)
    print("Example 1: Simple Scenario Generation")
    print("=" * 60)
    
    # Initialize LLM integration
    llm = LLMIntegration()
    
    # Load schema and enums
    schema_path = Path("schema/scenario.schema.json")
    schema = json.loads(schema_path.read_text())
    
    enums = {
        "difficulty": ["easy", "medium", "hard"],
        "host_type": ["attacker", "victim", "web", "db", "ftp", "smb", "custom"],
        "service_type": ["nginx", "apache", "flask", "node", "mysql", "postgres", "vsftpd", "openssh", "samba", "custom"],
        "vuln_type": ["weak_password", "outdated_software", "misconfiguration", "default_creds", "exposed_service", 
                      "vulnerable_webapp", "directory_traversal", "sql_injection", "command_injection", "ssrf", "lateral_movement"],
        "network_type": ["bridge", "custom_bridge", "isolated", "public"],
    }
    
    # User description
    description = """
    Create a beginner-friendly web security lab with:
    - A web server running an old version of Apache
    - A SQL injection vulnerability in a login form
    - One flag hidden in the database
    - Should take about 30 minutes
    """
    
    print(f"\nUser Input:\n{description}\n")
    print("Generating scenario...\n")
    
    try:
        scenario = llm.author_scenario(
            user_description=description,
            schema=schema,
            enums=enums,
            use_few_shot=True,
        )
        
        print("✅ Generated Scenario:")
        print(json.dumps(scenario, indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")


def example_2_repair_loop():
    """Example: Repair invalid JSON"""
    print("\n" + "=" * 60)
    print("Example 2: JSON Repair")
    print("=" * 60)
    
    llm = LLMIntegration()
    
    # Intentionally broken JSON (missing required fields, invalid enums)
    broken_json = """
    {
        "metadata": {
            "name": "Test Lab",
            "difficulty": "super_hard",
            "version": "1.0"
        },
        "networks": [],
        "hosts": [],
        "flags": []
    }
    """
    
    errors = [
        "metadata.author: required field missing",
        "metadata.description: required field missing",
        "metadata.difficulty: must be one of ['easy', 'medium', 'hard']",
        "networks: must have at least 1 item",
        "hosts: must have at least 1 item",
        "flags: must have at least 1 item",
    ]
    
    schema_path = Path("schema/scenario.schema.json")
    schema = json.loads(schema_path.read_text())
    
    print(f"\nBroken JSON:\n{broken_json}\n")
    print(f"Errors:\n" + "\n".join(f"  - {e}" for e in errors) + "\n")
    print("Attempting repair...\n")
    
    try:
        repaired = llm.repair_scenario(
            broken_json=broken_json,
            errors=errors,
            schema=schema,
            max_attempts=3,
        )
        
        print("✅ Repaired Scenario:")
        print(json.dumps(repaired, indent=2))
        
    except Exception as e:
        print(f"❌ Repair failed: {e}")


def example_3_tiered_hints():
    """Example: Tiered hint system"""
    print("\n" + "=" * 60)
    print("Example 3: Tiered Hints")
    print("=" * 60)
    
    llm = LLMIntegration(enable_rag=False)  # Disable RAG for simplicity
    
    # Simplified scenario
    scenario = {
        "metadata": {"name": "Web SQLi Lab"},
        "narrative": {
            "objectives": ["Find SQL injection vulnerability", "Extract admin password"]
        }
    }
    
    # Simulated lab state
    lab_state = {
        "hosts": {
            "web": {"ip": "172.20.0.20", "status": "running"}
        },
        "solved_flags": [],
        "time_elapsed": 300,  # 5 minutes
    }
    
    # Get hints at each tier
    for tier in [HintTier.NUDGE, HintTier.DIRECTIONAL, HintTier.TECHNIQUE, HintTier.DETAILED]:
        print(f"\n--- Tier {tier.value}: {tier.name} ---")
        hint = llm.provide_hint(
            scenario=scenario,
            lab_state=lab_state,
            tier=tier,
        )
        print(hint)


def example_4_explanation():
    """Example: Concept explanation"""
    print("\n" + "=" * 60)
    print("Example 4: Concept Explanation")
    print("=" * 60)
    
    llm = LLMIntegration(enable_rag=False)
    
    scenario = {
        "metadata": {"name": "SQL Injection Lab"},
        "vulnerabilities": [
            {
                "type": "sql_injection",
                "description": "Login form vulnerable to SQL injection"
            }
        ]
    }
    
    event_log = [
        {"action": "scan", "details": "Discovered web server on port 80"},
        {"action": "exploit", "details": "Attempted SQL injection: ' OR '1'='1"},
        {"action": "success", "details": "Bypassed authentication"},
        {"action": "flag", "details": "Captured flag from database"},
    ]
    
    print("\nTopic: SQL Injection\n")
    print("Generating explanation...\n")
    
    explanation = llm.explain_topic(
        topic="SQL Injection",
        scenario=scenario,
        event_log=event_log,
    )
    
    print(explanation)


def example_5_interactive_authoring():
    """Example: Interactive authoring with validation"""
    print("\n" + "=" * 60)
    print("Example 5: Interactive Authoring")
    print("=" * 60)
    
    # This would require a validator implementation
    # Placeholder for demonstration
    print("\nThis example requires the validator module (Phase 3)")
    print("See integration.py -> interactive_authoring() for implementation")


def main():
    """Run all examples"""
    print("\n🤖 LLM Integration Examples\n")
    
    # Check if Ollama is available
    try:
        adapter = OllamaAdapter()
        print("✅ Ollama connection successful\n")
    except RuntimeError as e:
        print(f"❌ {e}")
        print("\nPlease ensure:")
        print("1. Ollama is installed: https://ollama.ai")
        print("2. Ollama is running: ollama serve")
        print("3. Model is downloaded: ollama pull llama3.2:latest")
        return
    
    # Run examples
    try:
        example_1_simple_generation()
        # example_2_repair_loop()
        # example_3_tiered_hints()
        # example_4_explanation()
        # example_5_interactive_authoring()
        
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
