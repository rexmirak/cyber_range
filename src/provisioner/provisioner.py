"""
Provisioner module

Consumes a validated scenario and a PlanResult to produce Docker operations.
Supports dry-run mode to return intended operations without executing them.
"""
from dataclasses import dataclass
from typing import List, Dict, Any

from src.planner.planner import PlanResult
import subprocess
from typing import Callable, Optional


@dataclass
class ProvisionResult:
    operations: List[Dict[str, Any]]  # sequence of operations with type and args
    errors: List[str]

    @property
    def is_successful(self) -> bool:
        return len(self.errors) == 0


def _network_create_op(network_id: str, subnet: str | None) -> Dict[str, Any]:
    cmd = ["docker", "network", "create"]
    if subnet:
        cmd += ["--subnet", subnet]
    cmd += [network_id]
    return {
        "type": "network.create",
        "args": {"id": network_id, "subnet": subnet},
        "cmd": cmd,
    }


def _container_run_op(
    host: Dict[str, Any],
    network_id: str,
    ip: str | None,
    ports: List[Dict[str, Any]],
    isolate: bool = False,
) -> Dict[str, Any]:
    name = host.get("id")
    image = host.get("base_image") or "alpine:latest"
    cmd = ["docker", "run", "-d", "--name", name, "--network", network_id]
    if ip:
        cmd += ["--ip", ip]
    # Volumes
    volumes = host.get("volumes") or []
    vol_specs: List[Dict[str, str]] = []
    for v in volumes:
        # Support either dict {source, target} or string "src:dest"
        if isinstance(v, dict):
            src = v.get("source")
            tgt = v.get("target")
            if src and tgt:
                cmd += ["-v", f"{src}:{tgt}"]
                vol_specs.append({"source": src, "target": tgt})
        elif isinstance(v, str) and ":" in v:
            src, tgt = v.split(":", 1)
            cmd += ["-v", f"{src}:{tgt}"]
            vol_specs.append({"source": src, "target": tgt})

    # Resource limits (cpu, memory, disk)
    resources = host.get("resources") or {}
    cpu_limit = resources.get("cpu_limit")
    if cpu_limit:
        # Accepts float or string
        try:
            cpu_val = float(cpu_limit)
            cmd += ["--cpus", str(cpu_val)]
        except Exception:
            pass
    memory_limit = resources.get("memory_limit")
    if memory_limit:
        # Accepts Docker format: 512m, 2g, etc.
        cmd += ["--memory", str(memory_limit)]
    disk_limit = resources.get("disk_limit")
    if disk_limit:
        # Only supported by some storage drivers (e.g., overlay2)
        cmd += ["--storage-opt", f"size={disk_limit}"]
    # Environment variables
    env_map = host.get("env") or {}
    env_items = []
    if isinstance(env_map, dict):
        for k, v in env_map.items():
            cmd += ["-e", f"{k}={v}"]
            env_items.append({"key": k, "value": str(v)})
    # Isolation/security options
    security_opts: List[str] = []
    if isolate:
        # Conservative hardening set (adjustable later)
        security_opts = [
            "no-new-privileges:true",
        ]
        for opt in security_opts:
            cmd += ["--security-opt", opt]
        # Read-only root fs + limited pids can be added optionally
        cmd += ["--read-only", "--pids-limit", "256"]
    
    # Restart policy
    restart_policy = host.get("restart_policy")
    if restart_policy:
        cmd += ["--restart", str(restart_policy)]
    
    # Healthcheck
    healthcheck = host.get("healthcheck")
    if healthcheck and isinstance(healthcheck, dict):
        test = healthcheck.get("test")
        if test:
            cmd += ["--health-cmd", str(test)]
        interval = healthcheck.get("interval")
        if interval:
            cmd += ["--health-interval", str(interval)]
        timeout = healthcheck.get("timeout")
        if timeout:
            cmd += ["--health-timeout", str(timeout)]
        retries = healthcheck.get("retries")
        if retries:
            cmd += ["--health-retries", str(retries)]
        start_period = healthcheck.get("start_period")
        if start_period:
            cmd += ["--health-start-period", str(start_period)]
    
    # Ports
    for p in ports:
        internal = p.get("internal")
        external = p.get("external")
        protocol = p.get("protocol", "tcp")
        if external and internal:
            cmd += ["-p", f"{external}:{internal}/{protocol}"]
    cmd += [image]
    return {
        "type": "container.run",
        "args": {
            "name": name,
            "image": image,
            "network": network_id,
            "ip": ip,
            "ports": ports,
            "volumes": vol_specs,
            "env": env_items,
            "isolate": isolate,
            "security_opts": security_opts,
        },
        "cmd": cmd,
    }


def _network_connect_op(container_name: str, network_id: str, ip: str | None) -> Dict[str, Any]:
    cmd = ["docker", "network", "connect"]
    if ip:
        cmd += ["--ip", ip]
    cmd += [network_id, container_name]
    return {
        "type": "network.connect",
        "args": {"container": container_name, "network": network_id, "ip": ip},
        "cmd": cmd,
    }


def _wait_for_health_op(container_name: str) -> Dict[str, Any]:
    """Generate operation to wait for container health"""
    return {
        "type": "healthcheck.wait",
        "args": {"container": container_name},
        "cmd": ["# wait for health check"],
    }


def provision(
    plan: PlanResult,
    scenario: Dict[str, Any],
    dry_run: bool = True,
    executor: Optional[Callable[[List[str]], tuple[int, str, str]]] = None,
    isolate: bool = False,
    idempotent_mode: str = "skip",  # "skip" (default) or "replace"
    parallel: bool = False,  # Enable parallel provisioning for independent hosts
) -> ProvisionResult:
    """
    Create networks and containers based on the plan. In dry_run mode return operations only.
    """
    ops: List[Dict[str, Any]] = []
    errors: List[str] = []

    # Helper: check if network/container exists (only if executor is available)
    def _network_exists(net: str) -> bool:
        if not executor:
            return False  # Assume not exists in dry-run
        try:
            code, _, _ = executor(["docker", "network", "inspect", net])
            return code == 0
        except Exception:
            return False

    def _container_exists(name: str) -> bool:
        if not executor:
            return False
        try:
            code, _, _ = executor(["docker", "container", "inspect", name])
            return code == 0
        except Exception:
            return False

    # Create networks first, with idempotency
    for net_id, net_info in (plan.network_topology or {}).items():
        exists = _network_exists(net_id)
        if exists:
            if idempotent_mode == "skip":
                # Skip creation, log as no-op
                ops.append({
                    "type": "network.create.skip",
                    "args": {"id": net_id, "subnet": net_info.get("subnet")},
                    "cmd": ["# network exists, skipping creation"]
                })
                continue
            elif idempotent_mode == "replace":
                # Remove and recreate
                ops.append({
                    "type": "network.remove",
                    "args": {"id": net_id},
                    "cmd": ["docker", "network", "rm", net_id],
                })
        ops.append(_network_create_op(net_id, net_info.get("subnet")))

    # Map host_id -> host definition for convenience
    hosts_by_id = {h.get("id"): h for h in scenario.get("hosts", [])}

    # Build dependency graph for parallel execution
    host_deps: Dict[str, List[str]] = {}
    for h in scenario.get("hosts", []):
        hid = h.get("id")
        if hid:
            host_deps[hid] = h.get("depends_on", []) or []

    # For each host in order, create container with appropriate network and ip(s), idempotent
    for hid in plan.ordered_components:
        host = hosts_by_id.get(hid)
        if not host:
            errors.append(f"Plan references unknown host '{hid}'")
            continue
        nets = host.get("networks", []) or []
        if not nets:
            errors.append(f"Host '{hid}' has no networks in scenario")
            continue
        ports = (plan.resource_allocation.get(hid, {}) or {}).get("ports", [])
        primary = nets[0]
        cname = host.get("id")
        exists = _container_exists(cname)
        if exists:
            if idempotent_mode == "skip":
                ops.append({
                    "type": "container.run.skip",
                    "args": {"name": cname},
                    "cmd": ["# container exists, skipping run"]
                })
            elif idempotent_mode == "replace":
                ops.append({
                    "type": "container.remove",
                    "args": {"name": cname},
                    "cmd": ["docker", "rm", "-f", cname],
                })
                ops.append(_container_run_op(
                    host,
                    primary.get("network_id"),
                    primary.get("ip_address"),
                    ports,
                    isolate=isolate,
                ))
        else:
            ops.append(_container_run_op(
                host,
                primary.get("network_id"),
                primary.get("ip_address"),
                ports,
                isolate=isolate,
            ))
        
        # Wait for health if healthcheck is defined
        if host.get("healthcheck") and not exists:
            ops.append(_wait_for_health_op(cname))
        
        for extra in nets[1:]:
            ops.append(
                _network_connect_op(
                    container_name=host.get("id"),
                    network_id=extra.get("network_id"),
                    ip=extra.get("ip_address"),
                )
            )

    # Execute if requested and an executor is provided
    if not dry_run and executor:
        import time
        import json
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Helper to wait for container health
        def _wait_for_container_health(container_name: str, timeout: int = 60) -> bool:
            """Wait for container to become healthy, return True on success"""
            start = time.time()
            while time.time() - start < timeout:
                try:
                    code, out, err = executor([
                        "docker", "inspect", "--format",
                        "{{json .State.Health}}", container_name
                    ])
                    if code == 0 and out.strip():
                        health_data = json.loads(out.strip())
                        status = health_data.get("Status", "")
                        if status == "healthy":
                            return True
                        elif status in ("none", ""):
                            # No healthcheck defined, consider ready
                            return True
                    # Check if container is at least running
                    code2, out2, _ = executor(["docker", "inspect", "--format", "{{.State.Running}}", container_name])
                    if code2 == 0 and out2.strip() == "true":
                        # Running but no health status yet, keep waiting
                        time.sleep(2)
                        continue
                    else:
                        return False
                except Exception:
                    pass
                time.sleep(2)
            return False
        
        def _execute_op(op: Dict[str, Any]) -> tuple[Dict[str, Any], Optional[str]]:
            """Execute a single operation, return (op, error_msg or None)"""
            t = op.get("type")
            cmd = op.get("cmd")
            if t and t.endswith(".skip"):
                return (op, None)
            if t == "healthcheck.wait":
                cname = op.get("args", {}).get("container")
                if cname:
                    if not _wait_for_container_health(cname):
                        return (op, f"Container '{cname}' did not become healthy in time")
                return (op, None)
            if not isinstance(cmd, list):
                return (op, f"Invalid command for op {t}: {cmd}")
            try:
                code, out, err = executor(cmd)
                if code != 0:
                    return (op, f"Command failed ({t}): {' '.join(cmd)} :: {err or out}")
                return (op, None)
            except Exception as e:
                return (op, f"Execution error for {t}: {e}")
        
        if parallel:
            # Group ops by dependency waves for parallel execution
            # Networks always first (sequential), then containers by wave
            network_ops = [o for o in ops if o["type"].startswith("network.")]
            container_ops = [o for o in ops if o["type"].startswith("container.") or o["type"] == "healthcheck.wait"]
            connect_ops = [o for o in ops if o["type"] == "network.connect"]
            
            # Execute networks sequentially first
            for op in network_ops:
                _, err = _execute_op(op)
                if err:
                    errors.append(err)
            
            # Build dependency waves for containers
            # Map container name to its operations (run, healthcheck.wait)
            container_op_map: Dict[str, List[Dict[str, Any]]] = {}
            for op in container_ops:
                if op["type"].startswith("container."):
                    cname = op["args"].get("name")
                    if cname:
                        if cname not in container_op_map:
                            container_op_map[cname] = []
                        container_op_map[cname].append(op)
                elif op["type"] == "healthcheck.wait":
                    cname = op["args"].get("container")
                    if cname:
                        if cname not in container_op_map:
                            container_op_map[cname] = []
                        container_op_map[cname].append(op)
            
            # Calculate dependency depth for each host
            def _calc_depth(hid: str, memo: Dict[str, int]) -> int:
                if hid in memo:
                    return memo[hid]
                deps = host_deps.get(hid, [])
                if not deps:
                    memo[hid] = 0
                    return 0
                max_dep_depth = max((_calc_depth(d, memo) for d in deps), default=-1)
                memo[hid] = max_dep_depth + 1
                return memo[hid]
            
            depth_memo: Dict[str, int] = {}
            host_depths: Dict[str, int] = {}
            for hid in plan.ordered_components:
                host_depths[hid] = _calc_depth(hid, depth_memo)
            
            # Group hosts by depth (wave)
            max_depth = max(host_depths.values(), default=0)
            for depth in range(max_depth + 1):
                wave_hosts = [hid for hid, d in host_depths.items() if d == depth]
                wave_ops: List[Dict[str, Any]] = []
                for hid in wave_hosts:
                    wave_ops.extend(container_op_map.get(hid, []))
                
                # Execute wave in parallel
                with ThreadPoolExecutor(max_workers=min(len(wave_ops), 4)) as pool:
                    futures = {pool.submit(_execute_op, op): op for op in wave_ops}
                    for future in as_completed(futures):
                        _, err = future.result()
                        if err:
                            errors.append(err)
            
            # Execute network connects sequentially after all containers
            for op in connect_ops:
                _, err = _execute_op(op)
                if err:
                    errors.append(err)
        else:
            # Sequential execution (original behavior)
            for op in ops:
                _, err = _execute_op(op)
                if err:
                    errors.append(err)

    return ProvisionResult(operations=ops, errors=errors)


def default_executor(cmd: List[str]) -> tuple[int, str, str]:
    """Default command executor using subprocess. Returns (code, stdout, stderr)."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError as e:
        return 127, "", str(e)
