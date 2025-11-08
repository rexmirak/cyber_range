from src.planner.planner import plan_scenario
from src.provisioner.provisioner import provision


def scenario_with_healthcheck():
    return {
        "metadata": {
            "name": "Healthcheck Lab", "version": "1.0.0",
            "difficulty": "easy", "author": "Test", "description": "desc"
        },
        "networks": [
            {"id": "net_dmz", "name": "dmz", "type": "custom_bridge", "subnet": "172.21.0.0/24"}
        ],
        "hosts": [
            {
                "id": "host_web",
                "name": "web",
                "type": "web",
                "base_image": "nginx:alpine",
                "networks": [
                    {"network_id": "net_dmz", "ip_address": "172.21.0.20"},
                ],
                "services": [],
                "restart_policy": "always",
                "healthcheck": {
                    "test": "curl -f http://localhost/ || exit 1",
                    "interval": "30s",
                    "timeout": "3s",
                    "retries": 3,
                    "start_period": "40s"
                },
                "flags": [],
                "vulnerabilities": [],
            }
        ],
        "flags": []
    }


def test_provision_includes_healthcheck_and_restart():
    sc = scenario_with_healthcheck()
    plan = plan_scenario(sc)
    result = provision(plan, sc, dry_run=True)
    run_ops = [op for op in result.operations if op["type"] == "container.run"]
    assert len(run_ops) == 1
    cmd = run_ops[0]["cmd"]
    
    # Check restart policy
    assert "--restart" in cmd and cmd[cmd.index("--restart") + 1] == "always"
    
    # Check healthcheck flags
    assert "--health-cmd" in cmd
    assert "--health-interval" in cmd and cmd[cmd.index("--health-interval") + 1] == "30s"
    assert "--health-timeout" in cmd and cmd[cmd.index("--health-timeout") + 1] == "3s"
    assert "--health-retries" in cmd and cmd[cmd.index("--health-retries") + 1] == "3"
    assert "--health-start-period" in cmd and cmd[cmd.index("--health-start-period") + 1] == "40s"


def test_provision_waits_for_health_before_network_connect():
    sc = scenario_with_healthcheck()
    # Add second network
    sc["networks"].append({
        "id": "net_internal", "name": "internal",
        "type": "custom_bridge", "subnet": "172.22.0.0/24"
    })
    sc["hosts"][0]["networks"].append({
        "network_id": "net_internal", "ip_address": "172.22.0.20"
    })
    
    plan = plan_scenario(sc)
    result = provision(plan, sc, dry_run=True)
    
    types = [op["type"] for op in result.operations]
    # Should have: network.create (x2), container.run, healthcheck.wait, network.connect
    assert "container.run" in types
    assert "healthcheck.wait" in types
    assert "network.connect" in types
    
    # Ensure healthcheck.wait comes before network.connect
    run_idx = types.index("container.run")
    wait_idx = types.index("healthcheck.wait")
    connect_idx = types.index("network.connect")
    assert run_idx < wait_idx < connect_idx


def test_provision_no_healthcheck_wait_if_no_healthcheck():
    sc = {
        "metadata": {
            "name": "No HC Lab", "version": "1.0.0", "difficulty": "easy",
            "author": "Test", "description": "desc"
        },
        "networks": [
            {"id": "net_dmz", "name": "dmz", "type": "custom_bridge", "subnet": "172.21.0.0/24"}
        ],
        "hosts": [
            {
                "id": "host_web",
                "name": "web",
                "type": "web",
                "base_image": "nginx:alpine",
                "networks": [
                    {"network_id": "net_dmz", "ip_address": "172.21.0.20"},
                ],
                "services": [],
                "flags": [],
                "vulnerabilities": [],
            }
        ],
        "flags": []
    }
    plan = plan_scenario(sc)
    result = provision(plan, sc, dry_run=True)
    types = [op["type"] for op in result.operations]
    assert "healthcheck.wait" not in types
