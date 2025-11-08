"""
Tests for resource policy engine
"""
import pytest
from src.provisioner.policy_engine import (
    PolicyEngine,
    ResourcePolicy,
    ResourceLimits,
    DifficultyTier,
    DEFAULT_POLICIES,
    create_default_engine
)


def test_resource_limits_to_dict():
    """Test ResourceLimits conversion to dictionary"""
    limits = ResourceLimits(
        cpu_limit=1.5,
        memory_limit="1g",
        disk_limit="10g",
        pids_limit=512
    )
    
    d = limits.to_dict()
    assert d["cpu_limit"] == 1.5
    assert d["memory_limit"] == "1g"
    assert d["disk_limit"] == "10g"
    assert d["pids_limit"] == 512


def test_resource_limits_to_dict_excludes_none():
    """Test ResourceLimits excludes None values"""
    limits = ResourceLimits(
        cpu_limit=1.0,
        memory_limit=None,
        disk_limit="5g"
    )
    
    d = limits.to_dict()
    assert "cpu_limit" in d
    assert "memory_limit" not in d
    assert "disk_limit" in d
    assert "pids_limit" not in d


def test_default_policies_exist():
    """Test that default policies are defined for all tiers"""
    assert DifficultyTier.EASY in DEFAULT_POLICIES
    assert DifficultyTier.MEDIUM in DEFAULT_POLICIES
    assert DifficultyTier.HARD in DEFAULT_POLICIES


def test_default_policy_easy_most_generous():
    """Test easy tier has most generous limits"""
    easy = DEFAULT_POLICIES[DifficultyTier.EASY]
    medium = DEFAULT_POLICIES[DifficultyTier.MEDIUM]
    hard = DEFAULT_POLICIES[DifficultyTier.HARD]
    
    assert easy.cpu_limit > medium.cpu_limit
    assert medium.cpu_limit > hard.cpu_limit
    assert easy.pids_limit > medium.pids_limit
    assert medium.pids_limit > hard.pids_limit


def test_resource_policy_from_tier():
    """Test creating policy from difficulty tier"""
    policy = ResourcePolicy.from_tier(DifficultyTier.MEDIUM)
    
    assert policy.tier == DifficultyTier.MEDIUM
    assert policy.limits.cpu_limit == 1.0
    assert policy.limits.memory_limit == "1g"
    assert policy.enforce_limits is True


def test_resource_policy_from_tier_custom_name():
    """Test creating policy from tier with custom name"""
    policy = ResourcePolicy.from_tier(DifficultyTier.HARD, name="my_hard_policy")
    
    assert policy.name == "my_hard_policy"
    assert policy.tier == DifficultyTier.HARD


def test_resource_policy_from_tier_custom_raises():
    """Test creating policy from CUSTOM tier raises error"""
    with pytest.raises(ValueError, match="Cannot create policy from CUSTOM tier"):
        ResourcePolicy.from_tier(DifficultyTier.CUSTOM)


def test_resource_policy_from_custom():
    """Test creating custom policy"""
    limits = ResourceLimits(
        cpu_limit=0.25,
        memory_limit="256m",
        pids_limit=128
    )
    policy = ResourcePolicy.from_custom("minimal", limits, allow_override=True)
    
    assert policy.name == "minimal"
    assert policy.tier == DifficultyTier.CUSTOM
    assert policy.limits.cpu_limit == 0.25
    assert policy.allow_override is True


def test_policy_engine_default_tier():
    """Test PolicyEngine uses default tier"""
    engine = PolicyEngine(default_tier=DifficultyTier.HARD)
    
    # Empty scenario should use default
    policy = engine.get_policy({})
    assert policy.tier == DifficultyTier.HARD


def test_policy_engine_register_custom_policy():
    """Test registering custom policy"""
    engine = PolicyEngine()
    custom_limits = ResourceLimits(cpu_limit=0.5, memory_limit="512m")
    custom_policy = ResourcePolicy.from_custom("test", custom_limits)
    
    engine.register_policy(custom_policy)
    
    assert "test" in engine.custom_policies
    assert engine.custom_policies["test"] == custom_policy


def test_policy_engine_get_policy_by_name():
    """Test getting policy by name from scenario"""
    engine = PolicyEngine()
    custom_limits = ResourceLimits(cpu_limit=0.5, memory_limit="512m")
    custom_policy = ResourcePolicy.from_custom("test", custom_limits)
    engine.register_policy(custom_policy)
    
    scenario_metadata = {"resource_policy": "test"}
    policy = engine.get_policy(scenario_metadata)
    
    assert policy.name == "test"
    assert policy.limits.cpu_limit == 0.5


def test_policy_engine_get_policy_by_difficulty():
    """Test getting policy by difficulty from scenario"""
    engine = PolicyEngine()
    
    scenario_metadata = {"difficulty": "hard"}
    policy = engine.get_policy(scenario_metadata)
    
    assert policy.tier == DifficultyTier.HARD


def test_policy_engine_get_policy_case_insensitive():
    """Test difficulty tier is case insensitive"""
    engine = PolicyEngine()
    
    scenario_metadata = {"difficulty": "EASY"}
    policy = engine.get_policy(scenario_metadata)
    
    assert policy.tier == DifficultyTier.EASY


def test_policy_engine_apply_policy_no_override():
    """Test applying policy without override"""
    engine = PolicyEngine()
    policy = ResourcePolicy.from_tier(DifficultyTier.MEDIUM)
    
    host_config = {"id": "test", "base_image": "alpine"}
    result = engine.apply_policy(host_config, policy)
    
    assert result["cpu_limit"] == 1.0
    assert result["memory_limit"] == "1g"
    assert result["disk_limit"] == "10g"
    assert result["pids_limit"] == 512


def test_policy_engine_apply_policy_with_override():
    """Test applying policy with override allowed"""
    engine = PolicyEngine()
    policy = ResourcePolicy.from_tier(DifficultyTier.MEDIUM)
    policy.allow_override = True
    
    # Host has custom limits
    host_config = {
        "id": "test",
        "base_image": "alpine",
        "cpu_limit": 2.0,
        "memory_limit": "2g"
    }
    result = engine.apply_policy(host_config, policy)
    
    # Should keep host limits
    assert result["cpu_limit"] == 2.0
    assert result["memory_limit"] == "2g"


def test_policy_engine_apply_policy_no_enforcement():
    """Test applying policy without enforcement"""
    engine = PolicyEngine()
    policy = ResourcePolicy.from_tier(DifficultyTier.MEDIUM)
    policy.enforce_limits = False
    
    host_config = {"id": "test", "base_image": "alpine"}
    result = engine.apply_policy(host_config, policy)
    
    # Should not add policy limits
    assert "cpu_limit" not in result


def test_policy_engine_validate_limits_valid():
    """Test validating compliant limits"""
    engine = PolicyEngine()
    policy = ResourcePolicy.from_tier(DifficultyTier.MEDIUM)
    
    host_config = {
        "cpu_limit": 0.5,  # Below policy max
        "memory_limit": "512m",
        "pids_limit": 256
    }
    
    is_valid, error = engine.validate_limits(host_config, policy)
    
    assert is_valid is True
    assert error is None


def test_policy_engine_validate_limits_cpu_exceeds():
    """Test validating CPU limit that exceeds policy"""
    engine = PolicyEngine()
    policy = ResourcePolicy.from_tier(DifficultyTier.MEDIUM)
    
    host_config = {
        "cpu_limit": 2.0,  # Exceeds policy max of 1.0
    }
    
    is_valid, error = engine.validate_limits(host_config, policy)
    
    assert is_valid is False
    assert "CPU limit" in error
    assert "exceeds" in error


def test_policy_engine_validate_limits_pids_exceeds():
    """Test validating PID limit that exceeds policy"""
    engine = PolicyEngine()
    policy = ResourcePolicy.from_tier(DifficultyTier.HARD)
    
    host_config = {
        "pids_limit": 1024,  # Exceeds policy max of 256
    }
    
    is_valid, error = engine.validate_limits(host_config, policy)
    
    assert is_valid is False
    assert "PID limit" in error


def test_policy_engine_validate_limits_no_enforcement():
    """Test validation passes when enforcement disabled"""
    engine = PolicyEngine()
    policy = ResourcePolicy.from_tier(DifficultyTier.MEDIUM)
    policy.enforce_limits = False
    
    host_config = {
        "cpu_limit": 10.0,  # Way over limit
    }
    
    is_valid, error = engine.validate_limits(host_config, policy)
    
    assert is_valid is True


def test_create_default_engine():
    """Test creating default policy engine"""
    engine = create_default_engine()
    
    assert engine.default_tier == DifficultyTier.MEDIUM
    assert "minimal" in engine.custom_policies
    assert "generous" in engine.custom_policies


def test_default_engine_has_minimal_policy():
    """Test default engine has minimal custom policy"""
    engine = create_default_engine()
    
    policy = engine.custom_policies["minimal"]
    assert policy.limits.cpu_limit == 0.25
    assert policy.limits.memory_limit == "256m"


def test_default_engine_has_generous_policy():
    """Test default engine has generous custom policy"""
    engine = create_default_engine()
    
    policy = engine.custom_policies["generous"]
    assert policy.limits.cpu_limit == 4.0
    assert policy.limits.memory_limit == "4g"
    assert policy.allow_override is True


def test_policy_priority_custom_over_difficulty():
    """Test custom policy name takes priority over difficulty"""
    engine = create_default_engine()
    
    # Scenario has both custom policy and difficulty
    scenario_metadata = {
        "resource_policy": "minimal",
        "difficulty": "easy"
    }
    
    policy = engine.get_policy(scenario_metadata)
    
    # Should use custom policy, not difficulty
    assert policy.name == "minimal"
    assert policy.limits.cpu_limit == 0.25
