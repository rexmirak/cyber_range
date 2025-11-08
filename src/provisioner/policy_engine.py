"""
Resource policy engine for tiered scenario constraints

Enforces resource limits based on scenario difficulty, tier, and custom policies.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class DifficultyTier(Enum):
    """Scenario difficulty levels"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    CUSTOM = "custom"


@dataclass
class ResourceLimits:
    """Resource constraints for a container"""
    cpu_limit: Optional[float] = None      # CPU cores (e.g., 1.5)
    memory_limit: Optional[str] = None     # Memory (e.g., "512m", "2g")
    disk_limit: Optional[str] = None       # Disk size (e.g., "10g")
    pids_limit: Optional[int] = None       # Max processes
    network_bandwidth: Optional[str] = None  # Not yet implemented in Docker
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values"""
        return {
            k: v for k, v in {
                "cpu_limit": self.cpu_limit,
                "memory_limit": self.memory_limit,
                "disk_limit": self.disk_limit,
                "pids_limit": self.pids_limit,
                "network_bandwidth": self.network_bandwidth,
            }.items() if v is not None
        }


# Default resource policies by difficulty tier
DEFAULT_POLICIES = {
    DifficultyTier.EASY: ResourceLimits(
        cpu_limit=2.0,          # 2 CPU cores
        memory_limit="2g",      # 2 GB RAM
        disk_limit="20g",       # 20 GB disk
        pids_limit=1024,        # 1024 processes
    ),
    DifficultyTier.MEDIUM: ResourceLimits(
        cpu_limit=1.0,          # 1 CPU core
        memory_limit="1g",      # 1 GB RAM
        disk_limit="10g",       # 10 GB disk
        pids_limit=512,         # 512 processes
    ),
    DifficultyTier.HARD: ResourceLimits(
        cpu_limit=0.5,          # 0.5 CPU cores
        memory_limit="512m",    # 512 MB RAM
        disk_limit="5g",        # 5 GB disk
        pids_limit=256,         # 256 processes
    ),
}


@dataclass
class ResourcePolicy:
    """Resource policy configuration"""
    name: str
    tier: DifficultyTier
    limits: ResourceLimits
    enforce_limits: bool = True
    allow_override: bool = False
    
    @classmethod
    def from_tier(cls, tier: DifficultyTier, name: Optional[str] = None) -> "ResourcePolicy":
        """Create policy from difficulty tier"""
        if tier == DifficultyTier.CUSTOM:
            raise ValueError("Cannot create policy from CUSTOM tier without limits")
        
        limits = DEFAULT_POLICIES[tier]
        policy_name = name or f"{tier.value}_policy"
        
        return cls(
            name=policy_name,
            tier=tier,
            limits=limits
        )
    
    @classmethod
    def from_custom(
        cls, name: str, limits: ResourceLimits,
        allow_override: bool = False
    ) -> "ResourcePolicy":
        """Create custom policy with specific limits"""
        return cls(
            name=name,
            tier=DifficultyTier.CUSTOM,
            limits=limits,
            allow_override=allow_override
        )


class PolicyEngine:
    """Enforces resource policies on scenarios"""
    
    def __init__(self, default_tier: DifficultyTier = DifficultyTier.MEDIUM):
        """Initialize policy engine with default tier"""
        self.default_tier = default_tier
        self.custom_policies: Dict[str, ResourcePolicy] = {}
        
    def register_policy(self, policy: ResourcePolicy):
        """Register a custom policy"""
        self.custom_policies[policy.name] = policy
    
    def get_policy(self, scenario_metadata: Dict[str, Any]) -> ResourcePolicy:
        """
        Determine resource policy for a scenario
        
        Priority:
        1. Scenario-specific custom policy by name
        2. Scenario difficulty tier
        3. Default tier
        """
        # Check for custom policy by name
        if "resource_policy" in scenario_metadata:
            policy_name = scenario_metadata["resource_policy"]
            if policy_name in self.custom_policies:
                return self.custom_policies[policy_name]
        
        # Check for difficulty tier
        if "difficulty" in scenario_metadata:
            difficulty = scenario_metadata["difficulty"].lower()
            try:
                tier = DifficultyTier(difficulty)
                if tier != DifficultyTier.CUSTOM:
                    return ResourcePolicy.from_tier(tier)
            except ValueError:
                pass  # Invalid difficulty, fall through to default
        
        # Use default tier
        return ResourcePolicy.from_tier(self.default_tier)
    
    def apply_policy(
        self, host_config: Dict[str, Any],
        policy: ResourcePolicy
    ) -> Dict[str, Any]:
        """
        Apply policy limits to host configuration

        If policy allows override and host has custom limits, keep host limits.
        Otherwise, enforce policy limits.
        """
        result = host_config.copy()
        
        # Check if host already has resource limits
        has_custom_limits = any(
            key in host_config
            for key in ["cpu_limit", "memory_limit", "disk_limit", "pids_limit"]
        )

        # If policy allows override and host has custom limits, keep them
        if policy.allow_override and has_custom_limits:
            return result

        # Enforce policy limits
        if policy.enforce_limits:
            limits = policy.limits.to_dict()
            result.update(limits)
        
        return result
    
    def validate_limits(
        self, host_config: Dict[str, Any],
        policy: ResourcePolicy
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that host limits don't exceed policy maximums

        Returns (is_valid, error_message)
        """
        if not policy.enforce_limits:
            return True, None
        
        errors = []
        
        # Check CPU limit
        if "cpu_limit" in host_config and policy.limits.cpu_limit:
            if host_config["cpu_limit"] > policy.limits.cpu_limit:
                errors.append(
                    f"CPU limit {host_config['cpu_limit']} exceeds "
                    f"policy maximum {policy.limits.cpu_limit}"
                )
        
        # Check memory limit
        if "memory_limit" in host_config and policy.limits.memory_limit:
            # Validate format (in real impl would parse units)
            host_mem = host_config["memory_limit"]
            if not any(host_mem.endswith(u) for u in ["m", "g", "k", "M", "G", "K"]):
                errors.append(f"Invalid memory limit format: {host_mem}")

        # Check disk limit
        if "disk_limit" in host_config and policy.limits.disk_limit:
            # Validate format (in real impl would parse units)
            host_disk = host_config["disk_limit"]
            if not any(host_disk.endswith(u) for u in ["m", "g", "k", "M", "G", "K"]):
                errors.append(f"Invalid disk limit format: {host_disk}")
        
        # Check PID limit
        if "pids_limit" in host_config and policy.limits.pids_limit:
            if host_config["pids_limit"] > policy.limits.pids_limit:
                errors.append(
                    f"PID limit {host_config['pids_limit']} exceeds "
                    f"policy maximum {policy.limits.pids_limit}"
                )
        
        if errors:
            return False, "; ".join(errors)
        
        return True, None


def create_default_engine() -> PolicyEngine:
    """Create policy engine with sensible defaults"""
    engine = PolicyEngine(default_tier=DifficultyTier.MEDIUM)
    
    # Register some example custom policies
    engine.register_policy(
        ResourcePolicy.from_custom(
            name="minimal",
            limits=ResourceLimits(
                cpu_limit=0.25,
                memory_limit="256m",
                disk_limit="2g",
                pids_limit=128
            )
        )
    )
    
    engine.register_policy(
        ResourcePolicy.from_custom(
            name="generous",
            limits=ResourceLimits(
                cpu_limit=4.0,
                memory_limit="4g",
                disk_limit="50g",
                pids_limit=2048
            ),
            allow_override=True
        )
    )
    
    return engine
