from src.planner.planner import plan_scenario
from src.provisioner.provisioner import provision


def scenario_with_env_vol():
    return {
        "metadata": {"name": "EnvVol Lab", "version": "1.0.0", "difficulty": "easy", "author": "Test", "description": "desc"},
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
                "env": {"FOO": "bar", "NUM": 1},
                "volumes": [
                    {"source": "/host/data", "target": "/data"},
                    "/host/logs:/var/log/app",
                ],
                "flags": [],
                "vulnerabilities": [],
            }
        ],
        "flags": []
    }


def test_provision_includes_env_volumes_and_isolation():
    sc = scenario_with_env_vol()
    plan = plan_scenario(sc)
    result = provision(plan, sc, dry_run=True, isolate=True)
    run_ops = [op for op in result.operations if op["type"] == "container.run"]
    assert len(run_ops) == 1
    op = run_ops[0]
    cmd = op["cmd"]
    # Check env flags present
    assert "-e" in cmd and any(s.startswith("FOO=bar") or s.startswith("NUM=1") for s in cmd)
    # Check volume flags present
    assert "-v" in cmd and any(":/data" in s or ":/var/log/app" in s for s in cmd)
    # Check isolation flags
    assert "--security-opt" in cmd and any("no-new-privileges" in s for s in cmd)
    assert "--read-only" in cmd
    # Args carry env/volumes metadata
    assert op["args"].get("env") and op["args"].get("volumes")
