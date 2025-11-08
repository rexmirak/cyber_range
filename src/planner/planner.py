"""
Planner module for Cyber Range Scenario Deployer

Responsibilities:
- Dependency resolution between scenario components
- Deployment order calculation
- Network topology planning
- Resource allocation

Interfaces:
- plan_scenario(scenario: dict) -> PlanResult

"""
from typing import Dict, Any, List, Tuple, Set, Optional
from dataclasses import dataclass

@dataclass
class PlanResult:
    ordered_components: List[str]  # host IDs in deployment order
    network_topology: Dict[str, Any]  # network_id -> {subnet, hosts: [{host_id, ip}]}
    resource_allocation: Dict[str, Any]  # host_id -> {resources, ports}
    errors: List[str]
    warnings: List[str]

    @property
    def is_successful(self) -> bool:
        """Return True if planning produced no errors"""
        return len(self.errors) == 0

def plan_scenario(scenario: dict) -> PlanResult:
    """
    Analyze the scenario definition and produce a deployment plan.
    Args:
        scenario (dict): Validated scenario definition.
    Returns:
        PlanResult: Planning results including deployment order, topology, and resources.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Basic extraction with defaults
    networks: List[Dict[str, Any]] = scenario.get("networks", []) or []
    hosts: List[Dict[str, Any]] = scenario.get("hosts", []) or []
    services: List[Dict[str, Any]] = scenario.get("services", []) or []

    # Index networks and services by id
    network_by_id: Dict[str, Dict[str, Any]] = {n.get("id"): n for n in networks if n.get("id")}
    service_by_id: Dict[str, Dict[str, Any]] = {s.get("id"): s for s in services if s.get("id")}

    # Build network topology: network_id -> {subnet, hosts: [{host_id, ip}]}
    network_topology: Dict[str, Any] = {}
    # Track IP usage per network to detect conflicts
    ip_usage: Dict[str, Set[str]] = {}

    for net in networks:
        nid = net.get("id")
        if not nid:
            errors.append("Network missing 'id'")
            continue
        network_topology[nid] = {
            "subnet": net.get("subnet"),
            "hosts": []
        }
        ip_usage[nid] = set()

    # Validate host network refs and populate topology
    for h in hosts:
        hid = h.get("id")
        if not hid:
            errors.append("Host missing 'id'")
            continue
        for net_ref in h.get("networks", []) or []:
            if not isinstance(net_ref, dict):
                continue
            nid = net_ref.get("network_id")
            ip = net_ref.get("ip_address")
            if not nid:
                errors.append(f"Host '{hid}' has network entry without 'network_id'")
                continue
            if nid not in network_by_id:
                errors.append(f"Host '{hid}' references unknown network '{nid}'")
                continue
            # IP conflict detection on same network
            if ip:
                if ip in ip_usage[nid]:
                    errors.append(f"IP conflict on network '{nid}': {ip} already in use")
                else:
                    ip_usage[nid].add(ip)
            network_topology[nid]["hosts"].append({"host_id": hid, "ip": ip})

    # Resource allocation per host, including ports from referenced services
    resource_allocation: Dict[str, Any] = {}
    # Track external port usage to detect conflicts: (port, protocol) -> host_id/service_id
    external_port_usage: Dict[Tuple[int, str], str] = {}

    for h in hosts:
        hid = h.get("id")
        if not hid:
            # Already recorded above
            continue
        resources = h.get("resources", {}) or {}
        host_alloc = {
            "cpu_limit": resources.get("cpu_limit"),
            "memory_limit": resources.get("memory_limit"),
            "disk_limit": resources.get("disk_limit"),
            "ports": []  # list of {internal, external, protocol, service_id}
        }

        # Resolve services referenced by host
        for svc_id in h.get("services", []) or []:
            svc = service_by_id.get(svc_id)
            if not svc:
                errors.append(f"Host '{hid}' references undefined service '{svc_id}'")
                continue
            for p in svc.get("ports", []) or []:
                internal = p.get("internal")
                external = p.get("external")
                protocol = (p.get("protocol") or "tcp").lower()
                # Track external port conflicts only when external mapping is provided
                if isinstance(external, int):
                    key = (external, protocol)
                    if key in external_port_usage:
                        prev = external_port_usage[key]
                        errors.append(
                            f"External port conflict: {protocol}/{external} used by '{prev}' and host '{hid}' (service '{svc_id}')"
                        )
                    else:
                        external_port_usage[key] = f"{hid}:{svc_id}"
                host_alloc["ports"].append({
                    "internal": internal,
                    "external": external,
                    "protocol": protocol,
                    "service_id": svc_id,
                })

        # Warnings for missing resource limits (optional best-practice)
        if h.get("type") != "attacker":
            if not resources.get("cpu_limit"):
                warnings.append(f"Host '{hid}' missing cpu_limit")
            if not resources.get("memory_limit"):
                warnings.append(f"Host '{hid}' missing memory_limit")

        resource_allocation[hid] = host_alloc

    # Dependency graph (optional 'depends_on' list per host)
    # Build adjacency list and in-degree for Kahn topological sort
    host_ids = {h.get("id") for h in hosts if h.get("id")}
    adj: Dict[str, Set[str]] = {hid: set() for hid in host_ids}
    indegree: Dict[str, int] = {hid: 0 for hid in host_ids}

    for h in hosts:
        hid = h.get("id")
        if not hid:
            continue
        for dep in h.get("depends_on", []) or []:
            if dep not in host_ids:
                errors.append(f"Host '{hid}' depends_on unknown host '{dep}'")
                continue
            # Edge dep -> hid (deploy dep before hid)
            if hid not in adj[dep]:
                adj[dep].add(hid)
                indegree[hid] += 1

    # Topological sort if dependencies exist; else simple ordering later
    topo_order: List[str] = []
    if any(h.get("depends_on") for h in hosts):
        from collections import deque
        queue = deque([hid for hid, deg in indegree.items() if deg == 0])
        processed = 0
        while queue:
            cur = queue.popleft()
            topo_order.append(cur)
            processed += 1
            for nxt in adj[cur]:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)
        if processed != len(host_ids):
            errors.append("Cycle detected in host dependencies")
            # Fallback: do not trust partial topo_order; we'll still compute a deterministic order below
            topo_order = []

    # Deployment priority (infrastructure first); integrate topo layering if present

    # Deployment order: networks are implicit; order hosts alphabetically by type priority then by id
    # Priority: infrastructure first (db, smb, ftp), then web/custom/victim, attacker last.
    type_priority = {
        "db": 0,
        "smb": 0,
        "ftp": 0,
        "web": 1,
        "custom": 1,
        "victim": 1,
        "attacker": 2,
    }

    def host_sort_key(h: Dict[str, Any]) -> Tuple[int, str]:
        t = (h.get("type") or "victim").lower()
        return (type_priority.get(t, 1), h.get("id") or "")

    if topo_order:
        # Sort within topo_order by priority/id preserving dependency ordering
        ordered_components = sorted(topo_order, key=lambda hid: (
            type_priority.get(next((h.get("type") or "victim") for h in hosts if h.get("id") == hid), 1), hid
        ))
    else:
        ordered_components = [h.get("id") for h in sorted(hosts, key=host_sort_key) if h.get("id")]

    # Attacker last enforcement (move attacker ids to end if they accidentally appear earlier due to deps)
    attackers = [hid for hid in ordered_components if next((h.get("type") for h in hosts if h.get("id") == hid), "") == "attacker"]
    non_attackers = [hid for hid in ordered_components if hid not in attackers]
    ordered_components = non_attackers + attackers

    return PlanResult(
        ordered_components=ordered_components,
        network_topology=network_topology,
        resource_allocation=resource_allocation,
        errors=errors,
        warnings=warnings,
    )
