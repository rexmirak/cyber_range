"""
Security profiles for container isolation

Provides pre-defined and custom security configurations including:
- Seccomp profiles (syscall filtering)
- Capability dropping (Linux capabilities)
- User namespace remapping
- AppArmor/SELinux profiles
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class SecurityLevel(Enum):
    """Security isolation levels"""
    MINIMAL = "minimal"      # Basic isolation
    STANDARD = "standard"    # Default secure profile
    STRICT = "strict"        # Maximum security
    CUSTOM = "custom"        # User-defined profile


# Default seccomp profiles
SECCOMP_PROFILES = {
    "minimal": {
        "defaultAction": "SCMP_ACT_ALLOW",
        "syscalls": []
    },
    "standard": {
        "defaultAction": "SCMP_ACT_ERRNO",
        "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_X86", "SCMP_ARCH_X32"],
        "syscalls": [
            {
                "names": [
                    "accept", "accept4", "access", "adjtimex", "alarm", "bind",
                    "brk", "capget", "capset", "chdir", "chmod", "chown",
                    "chroot", "clock_getres", "clock_gettime", "clock_nanosleep",
                    "close", "connect", "copy_file_range", "creat", "dup",
                    "dup2", "dup3", "epoll_create", "epoll_create1", "epoll_ctl",
                    "epoll_ctl_old", "epoll_pwait", "epoll_wait", "eventfd",
                    "eventfd2", "execve", "execveat", "exit", "exit_group",
                    "faccessat", "fadvise64", "fallocate", "fanotify_mark",
                    "fchdir", "fchmod", "fchmodat", "fchown", "fchownat",
                    "fcntl", "fdatasync", "fgetxattr", "flistxattr", "flock",
                    "fork", "fremovexattr", "fsetxattr", "fstat", "fstatfs",
                    "fsync", "ftruncate", "futex", "getcpu", "getcwd", "getdents",
                    "getdents64", "getegid", "geteuid", "getgid", "getgroups",
                    "getitimer", "getpeername", "getpgid", "getpgrp", "getpid",
                    "getppid", "getpriority", "getrandom", "getresgid", "getresuid",
                    "getrlimit", "get_robust_list", "getrusage", "getsid",
                    "getsockname", "getsockopt", "get_thread_area", "gettid",
                    "gettimeofday", "getuid", "getxattr", "inotify_add_watch",
                    "inotify_init", "inotify_init1", "inotify_rm_watch", "io_cancel",
                    "ioctl", "io_destroy", "io_getevents", "ioprio_get", "ioprio_set",
                    "io_setup", "io_submit", "ipc", "kill", "lchown", "lgetxattr",
                    "link", "linkat", "listen", "listxattr", "llistxattr",
                    "lremovexattr", "lseek", "lsetxattr", "lstat", "madvise",
                    "memfd_create", "mincore", "mkdir", "mkdirat", "mknod",
                    "mknodat", "mlock", "mlock2", "mlockall", "mmap", "mmap2",
                    "mprotect", "mq_getsetattr", "mq_notify", "mq_open",
                    "mq_timedreceive", "mq_timedsend", "mq_unlink", "mremap",
                    "msgctl", "msgget", "msgrcv", "msgsnd", "msync", "munlock",
                    "munlockall", "munmap", "nanosleep", "newfstatat", "open",
                    "openat", "pause", "pipe", "pipe2", "poll", "ppoll", "prctl",
                    "pread64", "preadv", "prlimit64", "pselect6", "pwrite64",
                    "pwritev", "read", "readahead", "readlink", "readlinkat",
                    "readv", "recv", "recvfrom", "recvmmsg", "recvmsg", "remap_file_pages",
                    "removexattr", "rename", "renameat", "renameat2", "restart_syscall",
                    "rmdir", "rt_sigaction", "rt_sigpending", "rt_sigprocmask",
                    "rt_sigqueueinfo", "rt_sigreturn", "rt_sigsuspend", "rt_sigtimedwait",
                    "rt_tgsigqueueinfo", "sched_getaffinity", "sched_getattr",
                    "sched_getparam", "sched_get_priority_max", "sched_get_priority_min",
                    "sched_getscheduler", "sched_rr_get_interval", "sched_setaffinity",
                    "sched_setattr", "sched_setparam", "sched_setscheduler",
                    "sched_yield", "seccomp", "select", "semctl", "semget", "semop",
                    "semtimedop", "send", "sendfile", "sendfile64", "sendmmsg",
                    "sendmsg", "sendto", "setfsgid", "setfsuid", "setgid",
                    "setgroups", "setitimer", "setpgid", "setpriority", "setregid",
                    "setresgid", "setresuid", "setreuid", "setrlimit", "set_robust_list",
                    "setsid", "setsockopt", "set_thread_area", "set_tid_address",
                    "setuid", "setxattr", "shmat", "shmctl", "shmdt", "shmget",
                    "shutdown", "sigaltstack", "signalfd", "signalfd4", "sigreturn",
                    "socket", "socketcall", "socketpair", "splice", "stat", "statfs",
                    "symlink", "symlinkat", "sync", "sync_file_range", "syncfs",
                    "sysinfo", "tee", "tgkill", "time", "timer_create", "timer_delete",
                    "timerfd_create", "timerfd_gettime", "timerfd_settime",
                    "timer_getoverrun", "timer_gettime", "timer_settime", "times",
                    "tkill", "truncate", "umask", "uname", "unlink", "unlinkat",
                    "utime", "utimensat", "utimes", "vfork", "vmsplice", "wait4",
                    "waitid", "waitpid", "write", "writev"
                ],
                "action": "SCMP_ACT_ALLOW"
            }
        ]
    },
    "strict": {
        "defaultAction": "SCMP_ACT_ERRNO",
        "architectures": ["SCMP_ARCH_X86_64"],
        "syscalls": [
            {
                "names": [
                    "read", "write", "open", "close", "stat", "fstat", "lstat",
                    "poll", "lseek", "mmap", "mprotect", "munmap", "brk",
                    "rt_sigaction", "rt_sigprocmask", "rt_sigreturn", "ioctl",
                    "pread64", "pwrite64", "readv", "writev", "access", "pipe",
                    "select", "sched_yield", "mremap", "msync", "mincore",
                    "madvise", "shmget", "shmat", "shmctl", "dup", "dup2",
                    "pause", "nanosleep", "getitimer", "alarm", "setitimer",
                    "getpid", "sendfile", "socket", "connect", "accept",
                    "sendto", "recvfrom", "sendmsg", "recvmsg", "shutdown",
                    "bind", "listen", "getsockname", "getpeername", "socketpair",
                    "setsockopt", "getsockopt", "clone", "fork", "vfork",
                    "execve", "exit", "wait4", "kill", "uname", "fcntl",
                    "flock", "fsync", "fdatasync", "truncate", "ftruncate",
                    "getdents", "getcwd", "chdir", "fchdir", "rename", "mkdir",
                    "rmdir", "creat", "link", "unlink", "symlink", "readlink",
                    "chmod", "fchmod", "chown", "fchown", "lchown", "umask",
                    "gettimeofday", "getrlimit", "getrusage", "sysinfo", "times",
                    "ptrace", "getuid", "syslog", "getgid", "setuid", "setgid",
                    "geteuid", "getegid", "setpgid", "getppid", "getpgrp",
                    "setsid", "setreuid", "setregid", "getgroups", "setgroups",
                    "setresuid", "getresuid", "setresgid", "getresgid", "getpgid",
                    "setfsuid", "setfsgid", "getsid", "capget", "capset",
                    "rt_sigpending", "rt_sigtimedwait", "rt_sigqueueinfo",
                    "rt_sigsuspend", "sigaltstack", "utime", "mknod", "uselib",
                    "personality", "ustat", "statfs", "fstatfs", "sysfs",
                    "getpriority", "setpriority", "sched_setparam", "sched_getparam",
                    "sched_setscheduler", "sched_getscheduler", "sched_get_priority_max",
                    "sched_get_priority_min", "sched_rr_get_interval", "mlock",
                    "munlock", "mlockall", "munlockall", "vhangup", "modify_ldt",
                    "pivot_root", "prctl", "arch_prctl", "adjtimex", "setrlimit",
                    "chroot", "sync", "acct", "settimeofday", "mount", "umount2"
                ],
                "action": "SCMP_ACT_ALLOW"
            }
        ]
    }
}

# Default capabilities to drop (Linux capabilities)
DEFAULT_CAP_DROP = [
    "ALL"  # Drop all by default, then add back specific ones needed
]

DEFAULT_CAP_ADD = [
    "CHOWN",  # Change file ownership
    "DAC_OVERRIDE",  # Bypass file permission checks
    "FOWNER",  # Bypass permission checks for file operations
    "FSETID",  # Allow setting file capabilities
    "KILL",  # Send signals to processes
    "SETGID",  # Set GID
    "SETUID",  # Set UID
    "SETPCAP",  # Modify process capabilities
    "NET_BIND_SERVICE",  # Bind to ports < 1024
    "NET_RAW",  # Use RAW and PACKET sockets
    "SYS_CHROOT",  # Use chroot()
    "AUDIT_WRITE",  # Write to audit log
]

# Dangerous capabilities that should rarely be enabled
DANGEROUS_CAPABILITIES = [
    "SYS_ADMIN",       # System administration operations
    "SYS_MODULE",      # Load/unload kernel modules
    "SYS_BOOT",        # Reboot system
    "SYS_NICE",        # Change process priority
    "SYS_RESOURCE",    # Override resource limits
    "SYS_TIME",        # Set system clock
    "SYS_TTY_CONFIG",  # Configure TTY devices
    "MKNOD",           # Create device nodes
    "MAC_ADMIN",       # MAC configuration
    "MAC_OVERRIDE",    # Override MAC policy
    "NET_ADMIN",       # Network administration
    "SYSLOG",          # Perform privileged syslog operations
    "DAC_READ_SEARCH",  # Bypass file read permission checks
    "LINUX_IMMUTABLE",  # Set immutable and append-only flags
    "IPC_LOCK",  # Lock memory
    "IPC_OWNER",  # Bypass permission checks for IPC
    "SYS_PTRACE",      # Trace arbitrary processes
    "SYS_PACCT",       # Use acct()
    "WAKE_ALARM",      # Trigger system wakeup events
    "BLOCK_SUSPEND",   # Block system suspend
]


@dataclass
class SecurityProfile:
    """Container security configuration"""
    name: str
    level: SecurityLevel
    
    # Seccomp
    seccomp_profile: Optional[str] = None  # Path to custom profile or built-in name
    seccomp_config: Optional[Dict[str, Any]] = None  # Inline seccomp config
    
    # Capabilities
    cap_drop: Optional[List[str]] = None  # Capabilities to drop
    cap_add: Optional[List[str]] = None   # Capabilities to add back
    
    # User namespace
    userns_mode: Optional[str] = None  # "host" or "remap"
    userns_remap: Optional[str] = None  # "user:group" for remapping
    
    # Additional security options
    no_new_privileges: bool = True
    read_only_rootfs: bool = False
    
    # AppArmor/SELinux
    apparmor_profile: Optional[str] = None
    selinux_label: Optional[str] = None
    
    # PID limits
    pids_limit: Optional[int] = None
    
    def __post_init__(self):
        """Set defaults based on security level"""
        if self.cap_drop is None:
            self.cap_drop = []
        if self.cap_add is None:
            self.cap_add = []
            
        if self.level == SecurityLevel.MINIMAL:
            # Minimal restrictions
            if not self.cap_drop:
                self.cap_drop = []
            if not self.cap_add:
                self.cap_add = []
            self.no_new_privileges = False
            self.read_only_rootfs = False
            
        elif self.level == SecurityLevel.STANDARD:
            # Balanced security
            if not self.cap_drop:
                self.cap_drop = ["ALL"]
            if not self.cap_add:
                self.cap_add = DEFAULT_CAP_ADD.copy()
            self.no_new_privileges = True
            self.read_only_rootfs = False
            if self.pids_limit is None:
                self.pids_limit = 512
            if self.seccomp_profile is None and self.seccomp_config is None:
                self.seccomp_profile = "standard"
                
        elif self.level == SecurityLevel.STRICT:
            # Maximum security
            if not self.cap_drop:
                self.cap_drop = ["ALL"]
            if not self.cap_add:
                # Only essential capabilities
                self.cap_add = ["CHOWN", "SETUID", "SETGID", "NET_BIND_SERVICE"]
            self.no_new_privileges = True
            self.read_only_rootfs = True
            if self.pids_limit is None:
                self.pids_limit = 256
            if self.seccomp_profile is None and self.seccomp_config is None:
                self.seccomp_profile = "strict"
            if self.userns_mode is None:
                self.userns_mode = "remap"
                # Default remap to dockremap user
                if self.userns_remap is None:
                    self.userns_remap = "dockremap:dockremap"


def get_builtin_profile(name: str) -> SecurityProfile:
    """Get a pre-defined security profile"""
    profiles = {
        "minimal": SecurityProfile(
            name="minimal",
            level=SecurityLevel.MINIMAL
        ),
        "standard": SecurityProfile(
            name="standard",
            level=SecurityLevel.STANDARD
        ),
        "strict": SecurityProfile(
            name="strict",
            level=SecurityLevel.STRICT
        ),
    }
    
    if name not in profiles:
        raise ValueError(f"Unknown security profile: {name}")
    
    return profiles[name]


def profile_to_docker_flags(profile: SecurityProfile) -> List[str]:
    """Convert security profile to Docker CLI flags"""
    flags = []
    
    # Seccomp
    if profile.seccomp_profile:
        if profile.seccomp_profile in SECCOMP_PROFILES:
            # Built-in profile - would need to write to temp file in real impl
            flags.extend(["--security-opt", f"seccomp={profile.seccomp_profile}"])
        else:
            # Custom profile path
            flags.extend(["--security-opt", f"seccomp={profile.seccomp_profile}"])
    elif profile.seccomp_config:
        # Inline config - would need to write to temp file
        flags.extend(["--security-opt", "seccomp=<inline>"])
    
    # Capabilities
    if profile.cap_drop:
        for cap in profile.cap_drop:
            flags.extend(["--cap-drop", cap])
    if profile.cap_add:
        for cap in profile.cap_add:
            flags.extend(["--cap-add", cap])
    
    # User namespace
    if profile.userns_mode == "remap" and profile.userns_remap:
        flags.extend(["--userns", f"remap:{profile.userns_remap}"])
    elif profile.userns_mode == "host":
        flags.extend(["--userns", "host"])
    
    # Security options
    if profile.no_new_privileges:
        flags.extend(["--security-opt", "no-new-privileges:true"])
    
    if profile.read_only_rootfs:
        flags.append("--read-only")
    
    # AppArmor
    if profile.apparmor_profile:
        flags.extend(["--security-opt", f"apparmor={profile.apparmor_profile}"])
    
    # SELinux
    if profile.selinux_label:
        flags.extend(["--security-opt", f"label={profile.selinux_label}"])
    
    # PID limit
    if profile.pids_limit:
        flags.extend(["--pids-limit", str(profile.pids_limit)])
    
    return flags
