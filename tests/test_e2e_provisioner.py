"""
End-to-end provisioner tests covering more execution paths
"""
from src.validator.scenario_validator import ScenarioValidator
from src.planner.planner import plan_scenario
from src.provisioner.provisioner import provision


def complex_scenario():
    """Complex scenario with dependencies, healthchecks, resources, and parallel opportunities"""
    return {
        "metadata": {
            "name": "Complex E2E Lab",
            "version": "1.0.0",
            "difficulty": "medium",
            "author": "Test",
            "description": "Complex scenario for E2E testing",
        },
        "networks": [
            {"id": "net_dmz", "name": "dmz", "type": "custom_bridge", "subnet": "172.30.0.0/24"},
            {"id": "net_internal", "name": "internal", "type": "custom_bridge", "subnet": "172.31.0.0/24"},
        ],
        "services": [
            {
                "id": "svc_web",
                "name": "nginx",
                "type": "nginx",
                "version": "1",
                "ports": [{"internal": 80, "external": 8080, "protocol": "tcp"}],
            },
            {
                "id": "svc_db",
                "name": "mysql",
                "type": "mysql",
                "version": "8",
                "ports": [{"internal": 3306, "protocol": "tcp"}],
            }
        ],
        "hosts": [
            {
                "id": "host_db",
                "name": "db",
                "type": "db",
                "base_image": "mysql:8",
                "networks": [{"network_id": "net_internal", "ip_address": "172.31.0.30"}],
                "services": ["svc_db"],
                "resources": {
                    "cpu_limit": "2.0",
                    "memory_limit": "1g",
                    "disk_limit": "10G"
                },
                "restart_policy": "unless-stopped",
                "healthcheck": {
                    "test": "mysqladmin ping -h localhost",
                    "interval": "10s",
                    "timeout": "5s",
                    "retries": 3,
                    "start_period": "30s"
                },
                "env": {
                    "MYSQL_ROOT_PASSWORD": "rootpass",
                    "MYSQL_DATABASE": "appdb"
                },
                "flags": [],
                "vulnerabilities": [],
            },
            {
                "id": "host_web",
                "name": "web",
                "type": "web",
                "base_image": "nginx:alpine",
                "networks": [
                    {"network_id": "net_dmz", "ip_address": "172.30.0.20"},
                    {"network_id": "net_internal", "ip_address": "172.31.0.20"},
                ],
                "services": ["svc_web"],
                "depends_on": ["host_db"],
                "resources": {
                    "cpu_limit": "1.0",
                    "memory_limit": "512m"
                },
                "restart_policy": "always",
                "healthcheck": {
                    "test": "wget -q --spider http://localhost/ || exit 1",
                    "interval": "15s",
                    "timeout": "3s",
                    "retries": 2
                },
                "volumes": [
                    {"source": "/host/web", "target": "/usr/share/nginx/html"}
                ],
                "flags": ["flag1"],
                "vulnerabilities": [],
            },
            {
                "id": "host_cache",
                "name": "cache",
                "type": "custom",
                "base_image": "redis:alpine",
                "networks": [{"network_id": "net_internal", "ip_address": "172.31.0.40"}],
                "services": [],
                "resources": {
                    "cpu_limit": "0.5",
                    "memory_limit": "256m"
                },
                "restart_policy": "on-failure",
                "flags": [],
                "vulnerabilities": [],
            },
            {
                "id": "host_attacker",
                "name": "attacker",
                "type": "attacker",
                "base_image": "kalilinux/kali-rolling",
                "networks": [{"network_id": "net_dmz", "ip_address": "172.30.0.10"}],
                "services": [],
                "flags": [],
                "vulnerabilities": [],
            },
        ],
        "flags": [
            {
                "id": "flag1",
                "name": "web_flag",
                "value": "FLAG{complex_scenario}",
                "points": 50,
                "placement": {
                    "type": "file",
                    "host_id": "host_web",
                    "details": {"path": "/var/www/flag.txt"},
                },
            }
        ],
    }


def test_e2e_complex_scenario_validation_plan_provision():
    """E2E test: validate, plan, and provision complex scenario"""
    scenario = complex_scenario()

    # Step 1: Validate
    validator = ScenarioValidator()
    vres = validator.validate(scenario)
    assert vres.is_valid, f"Validation failed: {vres.errors}"

    # Step 2: Plan
    plan = plan_scenario(scenario)
    assert plan.is_successful, f"Planning failed: {plan.errors}"
    
    # Check deployment order respects dependencies
    assert "host_db" in plan.ordered_components
    assert "host_web" in plan.ordered_components
    db_idx = plan.ordered_components.index("host_db")
    web_idx = plan.ordered_components.index("host_web")
    assert db_idx < web_idx, "DB should come before web due to dependency"
    
    # Attacker should be last
    assert plan.ordered_components[-1] == "host_attacker"
    
    # Check resource allocation includes all expected data
    for hid in ["host_db", "host_web", "host_cache"]:
        assert hid in plan.resource_allocation
        alloc = plan.resource_allocation[hid]
        assert "cpu_limit" in alloc
        assert "memory_limit" in alloc

    # Step 3: Provision (dry-run)
    pres_dry = provision(plan, scenario, dry_run=True, parallel=False)
    assert pres_dry.is_successful, f"Dry-run provision failed: {pres_dry.errors}"
    
    # Check operations were generated
    types = [op["type"] for op in pres_dry.operations]
    assert "network.create" in types
    assert "container.run" in types
    assert "network.connect" in types  # Web connects to 2nd network
    assert "healthcheck.wait" in types  # DB and Web have healthchecks

    # Step 4: Check parallel provisioning generates same ops
    pres_parallel = provision(plan, scenario, dry_run=True, parallel=True)
    assert pres_parallel.is_successful
    assert len(pres_parallel.operations) == len(pres_dry.operations)


def test_e2e_idempotency_replace_mode():
    """E2E test: provision with replace mode"""
    scenario = complex_scenario()
    plan = plan_scenario(scenario)
    
    # Mock executor that says everything exists
    def always_exists_executor(cmd):
        if "inspect" in cmd:
            return (0, "", "")  # exists
        return (0, "", "")
    
    # Provision with replace mode
    pres = provision(
        plan,
        scenario,
        dry_run=False,
        executor=always_exists_executor,
        idempotent_mode="replace"
    )
    
    types = [op["type"] for op in pres.operations]
    # Should have remove operations for existing resources
    assert "network.remove" in types
    assert "container.remove" in types
    # Should still create after removing
    assert "network.create" in types
    assert "container.run" in types


def test_e2e_isolation_and_resource_limits():
    """E2E test: verify isolation and resource limits are applied"""
    scenario = complex_scenario()
    plan = plan_scenario(scenario)
    
    # Provision with isolation enabled
    pres = provision(plan, scenario, dry_run=True, isolate=True)
    assert pres.is_successful
    
    # Check that isolation flags are present
    run_ops = [op for op in pres.operations if op["type"] == "container.run"]
    assert len(run_ops) == 4  # 4 hosts
    
    for op in run_ops:
        cmd = op["cmd"]
        # Check isolation flags
        if op["args"]["isolate"]:
            assert "--security-opt" in cmd
            assert "--read-only" in cmd
            assert "--pids-limit" in cmd
        
        # Check resource limits based on host
        hname = op["args"]["name"]
        if hname == "host_db":
            assert "--cpus" in cmd and cmd[cmd.index("--cpus") + 1] == "2.0"
            assert "--memory" in cmd and cmd[cmd.index("--memory") + 1] == "1g"
            assert "--storage-opt" in cmd
        elif hname == "host_web":
            assert "--cpus" in cmd and cmd[cmd.index("--cpus") + 1] == "1.0"
            assert "--memory" in cmd and cmd[cmd.index("--memory") + 1] == "512m"


def test_e2e_healthcheck_and_restart_policies():
    """E2E test: verify healthcheck and restart policies"""
    scenario = complex_scenario()
    plan = plan_scenario(scenario)
    
    pres = provision(plan, scenario, dry_run=True)
    assert pres.is_successful
    
    run_ops = [op for op in pres.operations if op["type"] == "container.run"]
    
    # Check DB host
    db_op = next((op for op in run_ops if op["args"]["name"] == "host_db"), None)
    assert db_op is not None
    cmd = db_op["cmd"]
    assert "--restart" in cmd and cmd[cmd.index("--restart") + 1] == "unless-stopped"
    assert "--health-cmd" in cmd
    assert "--health-interval" in cmd and cmd[cmd.index("--health-interval") + 1] == "10s"
    assert "--health-retries" in cmd and cmd[cmd.index("--health-retries") + 1] == "3"
    
    # Check Web host
    web_op = next((op for op in run_ops if op["args"]["name"] == "host_web"), None)
    assert web_op is not None
    cmd = web_op["cmd"]
    assert "--restart" in cmd and cmd[cmd.index("--restart") + 1] == "always"
    assert "--health-cmd" in cmd
    
    # Check cache host
    cache_op = next((op for op in run_ops if op["args"]["name"] == "host_cache"), None)
    assert cache_op is not None
    cmd = cache_op["cmd"]
    assert "--restart" in cmd and cmd[cmd.index("--restart") + 1] == "on-failure"
