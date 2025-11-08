"""
Integration tests for orchestrator pipeline (validator + planner)
"""
from src.orchestrator.pipeline import validate_and_plan


def valid_scenario():
    return {
        "metadata": {
            "name": "Pipeline Lab",
            "version": "1.0.0",
            "difficulty": "easy",
            "estimated_time_minutes": 15,
            "author": "Test",
            "description": "Pipeline test"
        },
        "networks": [
            {"id": "net_dmz", "name": "dmz", "type": "custom_bridge", "subnet": "172.20.0.0/24"}
        ],
        "hosts": [
            {
                "id": "host_db",
                "name": "db",
                "type": "db",
                "base_image": "mysql:8",
                "networks": [{"network_id": "net_dmz", "ip_address": "172.20.0.30"}],
                "services": [],
                "flags": [],
                "vulnerabilities": [],
                "resources": {"cpu_limit": "0.5", "memory_limit": "256m"}
            },
            {
                "id": "host_web",
                "name": "web",
                "type": "web",
                "base_image": "nginx:alpine",
                "networks": [{"network_id": "net_dmz", "ip_address": "172.20.0.20"}],
                "services": [],
                "flags": ["flag1"],
                "vulnerabilities": ["vuln1"]
            },
            {
                "id": "host_attacker",
                "name": "attacker",
                "type": "attacker",
                "base_image": "kalilinux/kali-rolling",
                "networks": [{"network_id": "net_dmz", "ip_address": "172.20.0.10"}],
                "services": []
            }
        ],
        "flags": [
            {
                "id": "flag1",
                "name": "f1",
                "value": "FLAG{1}",
                "points": 10,
                "placement": {
                    "type": "file",
                    "host_id": "host_web",
                    "details": {"path": "/flag.txt"},
                    "path": "/flag.txt"  # accommodate current validator semantic check
                }
            }
        ]
    }


def test_pipeline_happy_path():
    scenario = valid_scenario()
    validation, plan = validate_and_plan(scenario)
    assert validation.is_valid
    assert plan is not None
    assert plan.is_successful
    # Attacker should be last in ordering
    assert plan.ordered_components[-1] == "host_attacker"


def test_pipeline_validation_failure_short_circuits_planning():
    scenario = valid_scenario()
    # Break schema (missing required hosts array item)
    scenario["hosts"][0]["networks"][0]["network_id"] = "missing_net"
    validation, plan = validate_and_plan(scenario)
    assert not validation.is_valid
    assert plan is None
