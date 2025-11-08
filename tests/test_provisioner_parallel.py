from src.planner.planner import plan_scenario
from src.provisioner.provisioner import provision
import time
from threading import Lock


def scenario_with_dependencies():
    return {
        "metadata": {
            "name": "Parallel Lab", "version": "1.0.0", "difficulty": "easy",
            "author": "Test", "description": "desc"
        },
        "networks": [
            {"id": "net_dmz", "name": "dmz", "type": "custom_bridge", "subnet": "172.21.0.0/24"}
        ],
        "hosts": [
            {
                "id": "host_db",
                "name": "db",
                "type": "db",
                "base_image": "mysql:8",
                "networks": [{"network_id": "net_dmz", "ip_address": "172.21.0.30"}],
                "services": [],
                "flags": [],
                "vulnerabilities": [],
            },
            {
                "id": "host_web",
                "name": "web",
                "type": "web",
                "base_image": "nginx:alpine",
                "networks": [{"network_id": "net_dmz", "ip_address": "172.21.0.20"}],
                "services": [],
                "depends_on": ["host_db"],  # Web depends on DB
                "flags": [],
                "vulnerabilities": [],
            },
            {
                "id": "host_cache",
                "name": "cache",
                "type": "custom",
                "base_image": "redis:alpine",
                "networks": [{"network_id": "net_dmz", "ip_address": "172.21.0.40"}],
                "services": [],
                "flags": [],
                "vulnerabilities": [],
            },
        ],
        "flags": []
    }


def test_provision_parallel_dry_run():
    """Test parallel provisioning in dry-run mode"""
    sc = scenario_with_dependencies()
    plan = plan_scenario(sc)
    result = provision(plan, sc, dry_run=True, parallel=True)
    
    # Should still generate all operations
    types = [op["type"] for op in result.operations]
    assert types.count("container.run") == 3
    assert result.is_successful


def test_provision_parallel_execution_order():
    """Test that parallel execution respects dependencies"""
    sc = scenario_with_dependencies()
    plan = plan_scenario(sc)
    
    # Track execution order with timestamps
    execution_log = []
    lock = Lock()
    
    def tracking_executor(cmd):
        with lock:
            if len(cmd) > 2 and cmd[0] == "docker":
                if cmd[1] == "run" and "--name" in cmd:
                    name_idx = cmd.index("--name") + 1
                    if name_idx < len(cmd):
                        execution_log.append({
                            "action": "run",
                            "name": cmd[name_idx],
                            "time": time.time()
                        })
                elif cmd[1] == "network":
                    # Track network ops too
                    execution_log.append({
                        "action": "network",
                        "name": cmd[-1] if len(cmd) > 3 else "unknown",
                        "time": time.time()
                    })
                elif cmd[1] == "inspect" or (cmd[1] == "container" and len(cmd) > 2 and cmd[2] == "inspect"):
                    # Return non-existent for idempotency checks
                    return (1, "", "not found")
        # Simulate work
        time.sleep(0.05)
        return (0, "", "")
    
    result = provision(plan, sc, dry_run=False, executor=tracking_executor, parallel=True)
    assert result.is_successful
    
    # Extract container run times
    container_runs = [e for e in execution_log if e["action"] == "run"]
    assert len(container_runs) == 3, f"Expected 3 container runs, got {len(container_runs)}: {container_runs}"
    
    # host_db and host_cache should start before or at same time as host_web
    # (db/cache are independent, web depends on db)
    db_time = next((e["time"] for e in container_runs if e["name"] == "host_db"), None)
    cache_time = next((e["time"] for e in container_runs if e["name"] == "host_cache"), None)
    web_time = next((e["time"] for e in container_runs if e["name"] == "host_web"), None)
    
    assert db_time is not None, f"DB not found in: {container_runs}"
    assert cache_time is not None, f"Cache not found in: {container_runs}"
    assert web_time is not None, f"Web not found in: {container_runs}"
    
    # DB must complete before web starts (due to dependency)
    # Cache and DB can run in parallel
    assert db_time < web_time


def test_provision_parallel_faster_than_sequential():
    """Test that parallel is faster than sequential for independent hosts"""
    sc = {
        "metadata": {
            "name": "Parallel Speed Test", "version": "1.0.0",
            "difficulty": "easy", "author": "Test", "description": "desc"
        },
        "networks": [
            {"id": "net_dmz", "name": "dmz", "type": "custom_bridge", "subnet": "172.21.0.0/24"}
        ],
        "hosts": [
            {"id": f"host_{i}", "name": f"host{i}", "type": "custom", "base_image": "alpine:latest",
             "networks": [{"network_id": "net_dmz", "ip_address": f"172.21.0.{10+i}"}],
             "services": [], "flags": [], "vulnerabilities": []}
            for i in range(6)
        ],
        "flags": []
    }
    
    def slow_executor(cmd):
        # Handle inspect calls
        if "inspect" in cmd:
            return (1, "", "not found")
        # Simulate slow container creation
        time.sleep(0.1)
        return (0, "", "")
    
    plan = plan_scenario(sc)
    
    # Sequential execution
    start_seq = time.time()
    result_seq = provision(plan, sc, dry_run=False, executor=slow_executor, parallel=False)
    duration_seq = time.time() - start_seq
    
    # Parallel execution
    start_par = time.time()
    result_par = provision(plan, sc, dry_run=False, executor=slow_executor, parallel=True)
    duration_par = time.time() - start_par
    
    assert result_seq.is_successful
    assert result_par.is_successful
    
    # Parallel should be faster (6 hosts * 0.1s each = 0.6s sequential vs
    # ~0.2s parallel). Allow some overhead, but parallel should be at least
    # 20% faster
    assert duration_par < duration_seq * 0.8


def test_provision_sequential_still_works():
    """Ensure sequential mode (default) still works correctly"""
    sc = scenario_with_dependencies()
    plan = plan_scenario(sc)
    
    execution_order = []
    
    def tracking_executor(cmd):
        if "inspect" in cmd:
            return (1, "", "not found")
        if len(cmd) > 2 and cmd[0] == "docker" and cmd[1] == "run" and "--name" in cmd:
            name_idx = cmd.index("--name") + 1
            if name_idx < len(cmd):
                execution_order.append(cmd[name_idx])
        return (0, "", "")
    
    result = provision(plan, sc, dry_run=False, executor=tracking_executor, parallel=False)
    assert result.is_successful
    
    # In sequential mode, db should come before web (due to type priority and dependency)
    assert "host_db" in execution_order
    assert "host_web" in execution_order
    db_idx = execution_order.index("host_db")
    web_idx = execution_order.index("host_web")
    assert db_idx < web_idx
