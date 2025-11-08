"""
Unit tests for the planner module
"""
from src.planner.planner import plan_scenario, PlanResult


def minimal_valid_scenario():
    return {
        "metadata": {
            "name": "Test Lab",
            "version": "1.0.0",
            "difficulty": "easy",
            "estimated_time_minutes": 30,
            "author": "Test",
            "description": "Planner tests"
        },
        "networks": [
            {"id": "net_dmz", "name": "dmz", "type": "custom_bridge", "subnet": "172.20.0.0/24"}
        ],
        "hosts": [
            {
                "id": "host_web",
                "name": "web",
                "type": "web",
                "base_image": "nginx:alpine",
                "networks": [{"network_id": "net_dmz", "ip_address": "172.20.0.20"}],
                "services": [],
                "flags": [],
                "vulnerabilities": []
            },
            {
                "id": "host_attacker",
                "name": "attacker",
                "type": "attacker",
                "base_image": "kalilinux/kali-rolling",
                "networks": [{"network_id": "net_dmz", "ip_address": "172.20.0.10"}],
                "services": [],
                "flags": [],
                "vulnerabilities": []
            }
        ],
        "flags": [
            {
                "id": "flag1",
                "name": "f1",
                "value": "FLAG{1}",
                "points": 10,
                "placement": {"type": "file", "host_id": "host_web", "details": {"path": "/flag.txt"}}
            }
        ]
    }


def test_plan_valid_scenario_produces_order_and_topology():
    scenario = minimal_valid_scenario()
    result = plan_scenario(scenario)
    assert isinstance(result, PlanResult)
    assert result.is_successful
    # Contains both hosts, attacker last due to priority
    assert result.ordered_components[-1] == "host_attacker"
    assert set(result.ordered_components) == {"host_web", "host_attacker"}
    # Topology includes network and hosts with IPs
    topo = result.network_topology.get("net_dmz")
    assert topo and topo.get("subnet") == "172.20.0.0/24"
    hosts_on_net = {h["host_id"] for h in topo["hosts"]}
    assert hosts_on_net == {"host_web", "host_attacker"}


def test_ip_conflict_detection():
    scenario = minimal_valid_scenario()
    # Make duplicate IP on same network
    scenario["hosts"][1]["networks"][0]["ip_address"] = "172.20.0.20"
    result = plan_scenario(scenario)
    assert any("ip conflict" in e.lower() for e in result.errors)
    assert not result.is_successful


def test_missing_service_reference_error():
    scenario = minimal_valid_scenario()
    # Reference a service that doesn't exist
    scenario["hosts"][0]["services"] = ["svc_web"]
    result = plan_scenario(scenario)
    assert any("undefined service" in e.lower() for e in result.errors)
    assert not result.is_successful


def test_port_conflict_detection_across_hosts():
    scenario = minimal_valid_scenario()
    # Define two services mapping the same external port
    scenario["services"] = [
        {
            "id": "svc_web1",
            "name": "nginx",
            "type": "nginx",
            "version": "1",
            "ports": [{"internal": 80, "external": 8080, "protocol": "tcp"}]
        },
        {
            "id": "svc_web2",
            "name": "apache",
            "type": "apache",
            "version": "2",
            "ports": [{"internal": 80, "external": 8080, "protocol": "tcp"}]
        }
    ]
    # Attach each service to a different host
    scenario["hosts"][0]["services"] = ["svc_web1"]
    scenario["hosts"][1]["services"] = ["svc_web2"]

    result = plan_scenario(scenario)
    assert any("external port conflict" in e.lower() for e in result.errors)
    assert not result.is_successful


def test_unknown_network_reference_error():
    scenario = minimal_valid_scenario()
    scenario["hosts"][0]["networks"][0]["network_id"] = "net_unknown"
    result = plan_scenario(scenario)
    assert any("unknown network" in e.lower() for e in result.errors)
    assert not result.is_successful


def test_dependency_order_and_cycle_detection():
    scenario = minimal_valid_scenario()
    # Add dependencies: attacker depends on web
    scenario["hosts"][1]["depends_on"] = ["host_web"]
    result = plan_scenario(scenario)
    # Attacker should still appear last
    assert result.ordered_components[-1] == "host_attacker"
    assert result.is_successful

    # Introduce cycle: web depends on attacker
    scenario["hosts"][0]["depends_on"] = ["host_attacker"]
    result_cycle = plan_scenario(scenario)
    assert any("cycle" in e.lower() for e in result_cycle.errors)
    assert not result_cycle.is_successful


def test_resource_warnings():
    scenario = minimal_valid_scenario()
    # No resource limits will trigger warnings for non-attacker hosts
    result = plan_scenario(scenario)
    assert any("missing cpu_limit" in w.lower() for w in result.warnings)
    assert any("missing memory_limit" in w.lower() for w in result.warnings)
