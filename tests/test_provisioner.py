"""
Unit tests for provisioner dry-run
"""
from src.planner.planner import plan_scenario
from src.provisioner.provisioner import provision, ProvisionResult


def scenario():
    return {
        "metadata": {"name": "Provision Lab", "version": "1.0.0", "difficulty": "easy", "author": "Test", "description": "desc"},
        "networks": [
            {"id": "net_dmz", "name": "dmz", "type": "custom_bridge", "subnet": "172.21.0.0/24"}
        ],
        "hosts": [
            {"id": "host_db", "name": "db", "type": "db", "base_image": "mysql:8", "networks": [{"network_id": "net_dmz", "ip_address": "172.21.0.30"}], "services": [], "flags": [], "vulnerabilities": []},
            {"id": "host_web", "name": "web", "type": "web", "base_image": "nginx:alpine", "networks": [{"network_id": "net_dmz", "ip_address": "172.21.0.20"}], "services": [], "flags": [], "vulnerabilities": []},
            {"id": "host_attacker", "name": "attacker", "type": "attacker", "base_image": "kalilinux/kali-rolling", "networks": [{"network_id": "net_dmz", "ip_address": "172.21.0.10"}], "services": [], "flags": [], "vulnerabilities": []}
        ],
        "flags": [
            {"id": "flag1", "name": "flag1", "value": "FLAG{1}", "points": 10, "placement": {"type": "file", "host_id": "host_web", "details": {"path": "/flag.txt"}}}
        ]
    }


def test_provision_dry_run_operations():
    sc = scenario()
    plan = plan_scenario(sc)
    result = provision(plan, sc, dry_run=True)
    assert isinstance(result, ProvisionResult)
    assert result.is_successful
    # Expect one network create op and one container run per host
    types = [op["type"] for op in result.operations]
    assert types.count("network.create") == 1
    assert types.count("container.run") == 3
    # Attacker container should be last (due to ordered_components)
    last_run = [op for op in result.operations if op["type"] == "container.run"][-1]
    assert last_run["args"]["name"] == "host_attacker"


def test_provision_unknown_host_error():
    sc = scenario()
    plan = plan_scenario(sc)
    # Tamper plan to include a non-existent host id
    plan.ordered_components.append("ghost_host")
    result = provision(plan, sc, dry_run=True)
    assert any("unknown host" in e.lower() for e in result.errors)
    assert not result.is_successful


def test_provision_multi_network_host_connects_extras():
    sc = scenario()
    # Add a second network and attach web host to both
    sc["networks"].append({"id": "net_internal", "name": "internal", "type": "custom_bridge", "subnet": "172.22.0.0/24"})
    # Attach web to internal as second network
    for h in sc["hosts"]:
        if h["id"] == "host_web":
            h["networks"].append({"network_id": "net_internal", "ip_address": "172.22.0.20"})
            break
    plan = plan_scenario(sc)
    result = provision(plan, sc, dry_run=True)
    # Find ops for host_web
    web_ops = [op for op in result.operations if op["type"] in ("container.run", "network.connect") and (op["args"].get("name") == "host_web" or op["args"].get("container") == "host_web")]
    # Should have 1 run and 1 connect for the extra network
    assert len([op for op in web_ops if op["type"] == "container.run"]) == 1
    assert len([op for op in web_ops if op["type"] == "network.connect"]) == 1
    # Ensure primary run uses the first network (dmz)
    run_op = [op for op in web_ops if op["type"] == "container.run"][0]
    assert run_op["args"]["network"] == "net_dmz"
