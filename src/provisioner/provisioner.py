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


def provision(
    plan: PlanResult,
    scenario: Dict[str, Any],
    dry_run: bool = True,
    executor: Optional[Callable[[List[str]], tuple[int, str, str]]] = None,
    isolate: bool = False,
) -> ProvisionResult:
    """
    Create networks and containers based on the plan. In dry_run mode return operations only.
    """
    ops: List[Dict[str, Any]] = []
    errors: List[str] = []

    # Create networks first
    for net_id, net_info in (plan.network_topology or {}).items():
        ops.append(_network_create_op(net_id, net_info.get("subnet")))

    # Map host_id -> host definition for convenience
    hosts_by_id = {h.get("id"): h for h in scenario.get("hosts", [])}

    # For each host in order, create container with appropriate network and ip(s)
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
        ops.append(
            _container_run_op(
                host,
                primary.get("network_id"),
                primary.get("ip_address"),
                ports,
                isolate=isolate,
            )
        )
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
        # Stage 1: ensure networks exist before starting containers
        for op in [o for o in ops if o.get("type") == "network.create"]:
            cmd = op.get("cmd")
            if not isinstance(cmd, list):
                errors.append(f"Invalid command for op {op.get('type')}: {cmd}")
                continue
            try:
                code, out, err = executor(cmd)
                if code != 0:
                    errors.append(f"Command failed ({op.get('type')}): {' '.join(cmd)} :: {err or out}")
            except Exception as e:
                errors.append(f"Execution error for {op.get('type')}: {e}")
        # Optional: quick existence check (best effort)
        def _net_exists(net: str) -> bool:
            try:
                code, out, err = executor(["docker", "network", "inspect", net])
                return code == 0
            except Exception:
                return False

        # Stage 2: containers and network connects
        for op in [o for o in ops if o.get("type") != "network.create"]:
            # Guard: if container.run references a missing network, report clearly
            if op.get("type") == "container.run":
                net = op.get("args", {}).get("network")
                if net and not _net_exists(str(net)):
                    errors.append(f"Preflight: network '{net}' not found before container.run; network creation may have failed")
                    # Continue to attempt execution to capture docker's error as well
            cmd = op.get("cmd")
            if not isinstance(cmd, list):
                errors.append(f"Invalid command for op {op.get('type')}: {cmd}")
                continue
            try:
                code, out, err = executor(cmd)
                if code != 0:
                    errors.append(f"Command failed ({op.get('type')}): {' '.join(cmd)} :: {err or out}")
            except Exception as e:
                errors.append(f"Execution error for {op.get('type')}: {e}")

    return ProvisionResult(operations=ops, errors=errors)


def default_executor(cmd: List[str]) -> tuple[int, str, str]:
    """Default command executor using subprocess. Returns (code, stdout, stderr)."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError as e:
        return 127, "", str(e)
