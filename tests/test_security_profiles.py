"""
Tests for security profiles
"""
import pytest
from src.provisioner.security_profiles import (
    SecurityProfile,
    SecurityLevel,
    get_builtin_profile,
    profile_to_docker_flags,
    SECCOMP_PROFILES,
    DEFAULT_CAP_ADD,
)


def test_minimal_profile_defaults():
    """Test minimal security profile has minimal restrictions"""
    profile = SecurityProfile(name="test", level=SecurityLevel.MINIMAL)
    
    assert profile.no_new_privileges is False
    assert profile.read_only_rootfs is False
    assert profile.cap_drop == []
    assert profile.cap_add == []
    assert profile.pids_limit is None


def test_standard_profile_defaults():
    """Test standard security profile has balanced restrictions"""
    profile = SecurityProfile(name="test", level=SecurityLevel.STANDARD)
    
    assert profile.no_new_privileges is True
    assert profile.read_only_rootfs is False
    assert profile.cap_drop == ["ALL"]
    assert profile.cap_add == DEFAULT_CAP_ADD
    assert profile.pids_limit == 512
    assert profile.seccomp_profile == "standard"


def test_strict_profile_defaults():
    """Test strict security profile has maximum restrictions"""
    profile = SecurityProfile(name="test", level=SecurityLevel.STRICT)
    
    assert profile.no_new_privileges is True
    assert profile.read_only_rootfs is True
    assert profile.cap_drop == ["ALL"]
    assert len(profile.cap_add) == 4  # Only essential capabilities
    assert "CHOWN" in profile.cap_add
    assert "SETUID" in profile.cap_add
    assert profile.pids_limit == 256
    assert profile.seccomp_profile == "strict"
    assert profile.userns_mode == "remap"


def test_custom_profile():
    """Test custom security profile with explicit settings"""
    profile = SecurityProfile(
        name="custom",
        level=SecurityLevel.CUSTOM,
        cap_drop=["SYS_ADMIN", "NET_ADMIN"],
        cap_add=["NET_BIND_SERVICE"],
        seccomp_profile="/path/to/custom.json",
        userns_remap="testuser:testgroup",
        pids_limit=128
    )
    
    assert profile.cap_drop == ["SYS_ADMIN", "NET_ADMIN"]
    assert profile.cap_add == ["NET_BIND_SERVICE"]
    assert profile.seccomp_profile == "/path/to/custom.json"
    assert profile.userns_remap == "testuser:testgroup"
    assert profile.pids_limit == 128


def test_get_builtin_profile_minimal():
    """Test retrieving minimal built-in profile"""
    profile = get_builtin_profile("minimal")
    
    assert profile.name == "minimal"
    assert profile.level == SecurityLevel.MINIMAL


def test_get_builtin_profile_standard():
    """Test retrieving standard built-in profile"""
    profile = get_builtin_profile("standard")
    
    assert profile.name == "standard"
    assert profile.level == SecurityLevel.STANDARD


def test_get_builtin_profile_strict():
    """Test retrieving strict built-in profile"""
    profile = get_builtin_profile("strict")
    
    assert profile.name == "strict"
    assert profile.level == SecurityLevel.STRICT


def test_get_builtin_profile_invalid():
    """Test retrieving invalid profile raises error"""
    with pytest.raises(ValueError, match="Unknown security profile"):
        get_builtin_profile("nonexistent")


def test_profile_to_docker_flags_minimal():
    """Test minimal profile generates minimal flags"""
    profile = get_builtin_profile("minimal")
    flags = profile_to_docker_flags(profile)
    
    # Minimal profile should have very few flags
    assert len(flags) < 5


def test_profile_to_docker_flags_standard():
    """Test standard profile generates appropriate flags"""
    profile = get_builtin_profile("standard")
    flags = profile_to_docker_flags(profile)
    
    # Should have seccomp, capabilities, and pid limit
    assert "--security-opt" in flags
    assert "no-new-privileges:true" in flags
    assert "--cap-drop" in flags
    assert "ALL" in flags
    assert "--cap-add" in flags
    assert "--pids-limit" in flags
    assert "512" in flags


def test_profile_to_docker_flags_strict():
    """Test strict profile generates strict flags"""
    profile = get_builtin_profile("strict")
    flags = profile_to_docker_flags(profile)
    
    # Should have all security features
    assert "--security-opt" in flags
    assert "no-new-privileges:true" in flags
    assert "--cap-drop" in flags
    assert "ALL" in flags
    assert "--cap-add" in flags
    assert "--read-only" in flags
    assert "--pids-limit" in flags
    assert "256" in flags
    assert "--userns" in flags


def test_profile_to_docker_flags_custom_seccomp():
    """Test profile with custom seccomp path"""
    profile = SecurityProfile(
        name="custom",
        level=SecurityLevel.CUSTOM,
        seccomp_profile="/etc/docker/seccomp/custom.json"
    )
    flags = profile_to_docker_flags(profile)
    
    assert "--security-opt" in flags
    idx = flags.index("--security-opt")
    assert flags[idx + 1].startswith("seccomp=")


def test_profile_to_docker_flags_userns_remap():
    """Test profile with user namespace remapping"""
    profile = SecurityProfile(
        name="test",
        level=SecurityLevel.CUSTOM,
        userns_mode="remap",
        userns_remap="docker:docker"
    )
    flags = profile_to_docker_flags(profile)
    
    assert "--userns" in flags
    idx = flags.index("--userns")
    assert "remap:docker:docker" in flags[idx + 1]


def test_profile_to_docker_flags_apparmor():
    """Test profile with AppArmor profile"""
    profile = SecurityProfile(
        name="test",
        level=SecurityLevel.CUSTOM,
        apparmor_profile="docker-default"
    )
    flags = profile_to_docker_flags(profile)
    
    assert "--security-opt" in flags
    assert any("apparmor=" in f for f in flags)


def test_profile_to_docker_flags_selinux():
    """Test profile with SELinux label"""
    profile = SecurityProfile(
        name="test",
        level=SecurityLevel.CUSTOM,
        selinux_label="type:svirt_lxc_net_t"
    )
    flags = profile_to_docker_flags(profile)
    
    assert "--security-opt" in flags
    assert any("label=" in f for f in flags)


def test_seccomp_profiles_exist():
    """Test that built-in seccomp profiles are defined"""
    assert "minimal" in SECCOMP_PROFILES
    assert "standard" in SECCOMP_PROFILES
    assert "strict" in SECCOMP_PROFILES


def test_seccomp_standard_profile_structure():
    """Test standard seccomp profile has correct structure"""
    profile = SECCOMP_PROFILES["standard"]
    
    assert "defaultAction" in profile
    assert profile["defaultAction"] == "SCMP_ACT_ERRNO"
    assert "syscalls" in profile
    assert isinstance(profile["syscalls"], list)
    assert len(profile["syscalls"]) > 0
    
    # Check first syscall entry
    syscall_entry = profile["syscalls"][0]
    assert "names" in syscall_entry
    assert "action" in syscall_entry
    assert syscall_entry["action"] == "SCMP_ACT_ALLOW"


def test_seccomp_strict_profile_more_restrictive():
    """Test strict seccomp profile is more restrictive than standard"""
    standard = SECCOMP_PROFILES["standard"]
    strict = SECCOMP_PROFILES["strict"]
    
    # Count allowed syscalls
    standard_syscalls = set(standard["syscalls"][0]["names"])
    strict_syscalls = set(strict["syscalls"][0]["names"])
    
    # Strict should allow fewer syscalls than standard
    assert len(strict_syscalls) < len(standard_syscalls)
