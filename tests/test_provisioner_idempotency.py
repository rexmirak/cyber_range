from src.planner.planner import plan_scenario
from src.provisioner.provisioner import provision


def scenario():
    return {
        "metadata": {
            "name": "Idempotency Lab", "version": "1.0.0",
            "difficulty": "easy", "author": "Test", "description": "desc"
        },
        "networks": [
            {
                "id": "net_dmz", "name": "dmz", "type": "custom_bridge",
                "subnet": "172.21.0.0/24"
            }
        ],
        "hosts": [
            {
                "id": "host_web", "name": "web", "type": "web",
                "base_image": "nginx:alpine",
                "networks": [{
                    "network_id": "net_dmz", "ip_address": "172.21.0.20"
                }],
                "services": [], "flags": [], "vulnerabilities": []
            },
        ],
        "flags": []
    }


def test_idempotent_skip_mode():
    sc = scenario()
    plan = plan_scenario(sc)
    # Simulate executor: first call, nothing exists; second call, everything exists
    calls = {"net": 0, "container": 0}

    def fake_executor(cmd):
        if cmd[:3] == ["docker", "network", "inspect"]:
            calls["net"] += 1
            return (0 if calls["net"] > 1 else 1, "", "")  # exists on 2nd call
        if cmd[:3] == ["docker", "container", "inspect"]:
            calls["container"] += 1
            return (0 if calls["container"] > 1 else 1, "", "")  # exists on 2nd call
        return (0, "", "")
    # First run: should create
    result1 = provision(plan, sc, dry_run=False, executor=fake_executor, idempotent_mode="skip")
    types1 = [op["type"] for op in result1.operations]
    assert "network.create" in types1
    assert "container.run" in types1
    # Second run: should skip
    result2 = provision(plan, sc, dry_run=False, executor=fake_executor, idempotent_mode="skip")
    types2 = [op["type"] for op in result2.operations]
    assert any(t == "network.create.skip" for t in types2)
    assert any(t == "container.run.skip" for t in types2)


def test_idempotent_replace_mode():
    sc = scenario()
    plan = plan_scenario(sc)
    # Simulate executor: always exists

    def always_exists_executor(cmd):
        if cmd[:3] in (["docker", "network", "inspect"], ["docker", "container", "inspect"]):
            return (0, "", "")
        return (0, "", "")
    result = provision(plan, sc, dry_run=False, executor=always_exists_executor, idempotent_mode="replace")
    types = [op["type"] for op in result.operations]
    assert "network.remove" in types
    assert "container.remove" in types
    assert "network.create" in types
    assert "container.run" in types
