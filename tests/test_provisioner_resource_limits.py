from src.planner.planner import plan_scenario
from src.provisioner.provisioner import provision


def scenario_with_limits():
    return {
        "metadata": {
            "name": "Limits Lab", "version": "1.0.0", "difficulty": "easy",
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
                "networks": [{"network_id": "net_dmz", "ip_address": "172.21.0.20"}],
                "services": [],
                "resources": {
                    "cpu_limit": "1.5",
                    "memory_limit": "512m",
                    "disk_limit": "2G"
                },
                "flags": [],
                "vulnerabilities": [],
            }
        ],
        "flags": []
    }


def test_provision_includes_resource_limits():
    sc = scenario_with_limits()
    plan = plan_scenario(sc)
    result = provision(plan, sc, dry_run=True)
    run_ops = [op for op in result.operations if op["type"] == "container.run"]
    assert len(run_ops) == 1
    cmd = run_ops[0]["cmd"]
    # Check cpu flag
    assert "--cpus" in cmd and cmd[cmd.index("--cpus") + 1] == "1.5"
    # Check memory flag
    assert "--memory" in cmd and cmd[cmd.index("--memory") + 1] == "512m"
    # Check disk flag
    assert "--storage-opt" in cmd and "size=2G" in cmd
