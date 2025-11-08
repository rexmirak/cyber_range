"""
End-to-end test: mocked LLM authoring -> validate -> plan -> provision (dry-run)
This test does not require a running LLM; authoring is mocked to return a static scenario.
"""
from src.validator.scenario_validator import ScenarioValidator
from src.planner.planner import plan_scenario
from src.provisioner.provisioner import provision, ProvisionResult


def mocked_llm_author_scenario():
    return {
        "metadata": {
            "name": "Mocked Lab",
            "version": "1.0.0",
            "difficulty": "easy",
            "author": "Mock",
            "description": "E2E mocked scenario",
        },
        "networks": [
            {"id": "net_a", "name": "dmz", "type": "custom_bridge", "subnet": "172.30.0.0/24"},
            {"id": "net_b", "name": "internal", "type": "custom_bridge", "subnet": "172.31.0.0/24"},
        ],
        "services": [
            {
                "id": "svc_web",
                "name": "nginx",
                "type": "nginx",
                "version": "1",
                "ports": [{"internal": 80, "external": 8081, "protocol": "tcp"}],
            }
        ],
        "hosts": [
            {
                "id": "host_web",
                "name": "web",
                "type": "web",
                "base_image": "nginx:alpine",
                "networks": [
                    {"network_id": "net_a", "ip_address": "172.30.0.20"},
                    {"network_id": "net_b", "ip_address": "172.31.0.20"},
                ],
                "services": ["svc_web"],
                "flags": ["flag1"],
                "vulnerabilities": [],
            },
            {
                "id": "host_attacker",
                "name": "attacker",
                "type": "attacker",
                "base_image": "kalilinux/kali-rolling",
                "networks": [{"network_id": "net_a", "ip_address": "172.30.0.10"}],
                "services": [],
                "flags": [],
                "vulnerabilities": [],
            },
        ],
        "flags": [
            {
                "id": "flag1",
                "name": "f1",
                "value": "FLAG{MOCK}",
                "points": 10,
                "placement": {
                    "type": "file",
                    "host_id": "host_web",
                    "details": {"path": "/flag.txt"},
                },
            }
        ],
    }


def test_e2e_mocked_author_to_dryrun_provision():
    # 1) Author (mocked)
    scenario = mocked_llm_author_scenario()

    # 2) Validate
    validator = ScenarioValidator()
    vres = validator.validate(scenario)
    assert vres.is_valid, f"Validation failed: {[str(e) for e in vres.errors]}"

    # 3) Plan
    plan = plan_scenario(scenario)
    assert plan.is_successful, f"Planning failed: {plan.errors}"
    assert plan.ordered_components[-1] == "host_attacker"

    # 4) Provision (dry-run)
    pres = provision(plan, scenario, dry_run=True)
    assert isinstance(pres, ProvisionResult)
    assert pres.is_successful
    # Expect: networks created (2) and runs/connects
    types = [op["type"] for op in pres.operations]
    assert types.count("network.create") == 2
    assert types.count("container.run") == 2
    assert types.count("network.connect") == 1  # web connected to second network
