# Scenario JSON Schema

## Overview
The scenario JSON defines a complete cyber range lab including metadata, network topology, hosts, services, vulnerabilities, flags, and learning objectives.

## Full Schema Structure

```json
{
  "metadata": {
    "name": "string",
    "description": "string",
    "author": "string",
    "version": "string",
    "difficulty": "easy | medium | hard",
    "estimated_time_minutes": "number",
    "tags": ["string"],
    "learning_objectives": ["string"]
  },
  "networks": [
    {
      "id": "string",
      "name": "string",
      "type": "bridge | custom_bridge | isolated | public",
      "subnet": "string (CIDR notation)",
      "gateway": "string (optional)",
      "dns": ["string (optional)"]
    }
  ],
  "hosts": [
    {
      "id": "string",
      "name": "string",
      "type": "attacker | victim | web | db | ftp | smb | custom",
      "base_image": "string (Docker image)",
      "networks": [
        {
          "network_id": "string",
          "ip_address": "string (static IP, optional)"
        }
      ],
      "resources": {
        "cpu_limit": "string (e.g., '1.0')",
        "memory_limit": "string (e.g., '512m')",
        "disk_limit": "string (optional)"
      },
      "services": ["service_id"],
      "vulnerabilities": ["vulnerability_id"],
      "flags": ["flag_id"],
      "custom_config": {
        "dockerfile_path": "string (optional)",
        "build_args": {},
        "environment": {},
        "volumes": [],
        "entrypoint": "string (optional)"
      }
    }
  ],
  "services": [
    {
      "id": "string",
      "name": "string",
      "type": "nginx | apache | flask | node | mysql | postgres | vsftpd | openssh | samba | custom",
      "version": "string",
      "ports": [
        {
          "internal": "number",
          "external": "number (optional, for host exposure)",
          "protocol": "tcp | udp"
        }
      ],
      "config": {
        "config_files": [
          {
            "path": "string",
            "content": "string (or template)"
          }
        ],
        "credentials": [
          {
            "username": "string",
            "password": "string",
            "role": "string (optional)"
          }
        ],
        "custom_setup": "string (bash script, optional)"
      }
    }
  ],
  "vulnerabilities": [
    {
      "id": "string",
      "name": "string",
      "type": "weak_password | outdated_software | misconfiguration | default_creds | exposed_service | vulnerable_webapp | directory_traversal | sql_injection | command_injection | ssrf | lateral_movement",
      "severity": "low | medium | high | critical",
      "description": "string",
      "cve": "string (optional)",
      "affected_service": "string (service_id, optional)",
      "exploitation_notes": "string (optional)",
      "remediation": "string (optional)",
      "setup": {
        "module": "string (path to vuln module script)",
        "parameters": {}
      }
    }
  ],
  "flags": [
    {
      "id": "string",
      "name": "string",
      "value": "string (or generated)",
      "placement": {
        "type": "file | env | service_response | db_row",
        "host_id": "string",
        "details": {
          "path": "string (for file)",
          "env_var": "string (for env)",
          "endpoint": "string (for service_response)",
          "table": "string (for db_row)",
          "query": "string (for db_row)"
        }
      },
      "points": "number",
      "hint": "string (optional)"
    }
  ],
  "scoring": {
    "total_points": "number",
    "passing_score": "number",
    "time_bonus": "boolean",
    "penalty_for_hints": "boolean"
  },
  "narrative": {
    "scenario_background": "string",
    "attacker_role": "string",
    "objectives": ["string"],
    "success_criteria": "string"
  }
}
```

## Field Descriptions

### Metadata
- `name`: Short, descriptive name for the scenario
- `description`: Detailed explanation of what the lab covers
- `author`: Creator of the scenario
- `version`: Semantic version (e.g., "1.0.0")
- `difficulty`: Overall difficulty level
- `estimated_time_minutes`: Expected time to complete
- `tags`: Keywords for categorization (e.g., "web", "network", "privilege-escalation")
- `learning_objectives`: Specific skills/concepts the user will learn

### Networks
- `id`: Unique identifier for the network
- `name`: Human-readable name
- `type`: Network isolation level
  - `bridge`: Default Docker bridge
  - `custom_bridge`: User-defined Docker network
  - `isolated`: No external access except from attacker
  - `public`: Exposed to host for testing
- `subnet`: CIDR notation (e.g., "172.20.0.0/16")
- `gateway`: Optional gateway IP
- `dns`: Optional DNS servers

### Hosts
- `id`: Unique identifier for the host
- `name`: Human-readable hostname
- `type`: Role of the host in the scenario
- `base_image`: Docker image (e.g., "ubuntu:22.04", "kalilinux/kali-rolling")
- `networks`: Array of network connections with optional static IPs
- `resources`: Docker resource limits
- `services`: Array of service IDs to install/configure
- `vulnerabilities`: Array of vulnerability IDs to inject
- `flags`: Array of flag IDs to place on this host
- `custom_config`: Advanced Docker configuration

### Services
- `id`: Unique identifier for the service
- `name`: Human-readable service name
- `type`: Service category
- `version`: Specific version to install
- `ports`: Port mappings (internal required, external optional)
- `config`: Service-specific configuration
  - `config_files`: Configuration files to create/modify
  - `credentials`: Users/passwords for the service
  - `custom_setup`: Bash script for additional setup

### Vulnerabilities
- `id`: Unique identifier for the vulnerability
- `name`: Human-readable vulnerability name
- `type`: Vulnerability category
- `severity`: CVSS-like severity rating
- `description`: What the vulnerability is
- `cve`: CVE identifier if applicable
- `affected_service`: Which service has this vulnerability
- `exploitation_notes`: Hints for exploitation (for guide)
- `remediation`: How to fix the vulnerability (for learning)
- `setup`: Module and parameters to inject the vulnerability

### Flags
- `id`: Unique identifier for the flag
- `name`: Human-readable flag name
- `value`: The actual flag string (can use templates like `{random_uuid}`)
- `placement`: Where and how to place the flag
  - `file`: Store in a file at the specified path
  - `env`: Set as an environment variable
  - `service_response`: Return from a web endpoint or service
  - `db_row`: Insert into a database table
- `points`: Points awarded for capturing this flag
- `hint`: Optional hint for finding the flag

### Scoring
- `total_points`: Sum of all flag points
- `passing_score`: Minimum points to complete the lab
- `time_bonus`: Award bonus points for faster completion
- `penalty_for_hints`: Deduct points when hints are requested

### Narrative
- `scenario_background`: Story/context for the lab
- `attacker_role`: What role the user plays
- `objectives`: List of high-level goals
- `success_criteria`: What constitutes completion

## Validation Rules

1. All IDs must be unique within their category
2. All references (service_id, vulnerability_id, etc.) must exist
3. Network subnets must not overlap
4. IP addresses must be valid and within the specified subnet
5. Port numbers must be valid (1-65535)
6. Host types must match their intended services
7. At least one network and one host must be defined
8. At least one flag must be defined
9. Resource limits must be valid Docker resource specifications

## Example Minimal Scenario

```json
{
  "metadata": {
    "name": "Web SQL Injection Lab",
    "description": "Learn SQL injection basics",
    "author": "CyberRange Team",
    "version": "1.0.0",
    "difficulty": "easy",
    "estimated_time_minutes": 30,
    "tags": ["web", "sqli"],
    "learning_objectives": ["Identify SQL injection vulnerabilities", "Extract data using SQLi"]
  },
  "networks": [
    {
      "id": "net_main",
      "name": "main_network",
      "type": "custom_bridge",
      "subnet": "172.20.0.0/16"
    }
  ],
  "hosts": [
    {
      "id": "host_attacker",
      "name": "attacker",
      "type": "attacker",
      "base_image": "kalilinux/kali-rolling",
      "networks": [{"network_id": "net_main", "ip_address": "172.20.0.10"}],
      "resources": {"cpu_limit": "1.0", "memory_limit": "1g"},
      "services": [],
      "vulnerabilities": [],
      "flags": []
    },
    {
      "id": "host_web",
      "name": "webserver",
      "type": "web",
      "base_image": "php:7.4-apache",
      "networks": [{"network_id": "net_main", "ip_address": "172.20.0.20"}],
      "resources": {"cpu_limit": "0.5", "memory_limit": "512m"},
      "services": ["svc_web"],
      "vulnerabilities": ["vuln_sqli"],
      "flags": ["flag_admin_password"]
    }
  ],
  "services": [
    {
      "id": "svc_web",
      "name": "vulnerable_web_app",
      "type": "apache",
      "version": "2.4",
      "ports": [{"internal": 80, "protocol": "tcp"}],
      "config": {
        "credentials": [{"username": "admin", "password": "P@ssw0rd123"}]
      }
    }
  ],
  "vulnerabilities": [
    {
      "id": "vuln_sqli",
      "name": "SQL Injection in Login",
      "type": "sql_injection",
      "severity": "high",
      "description": "The login form is vulnerable to SQL injection",
      "affected_service": "svc_web",
      "setup": {
        "module": "modules/sqli_login.sh",
        "parameters": {}
      }
    }
  ],
  "flags": [
    {
      "id": "flag_admin_password",
      "name": "Admin Password",
      "value": "FLAG{sql_1nj3ct10n_m4st3r}",
      "placement": {
        "type": "db_row",
        "host_id": "host_web",
        "details": {
          "table": "users",
          "query": "SELECT password FROM users WHERE username='admin'"
        }
      },
      "points": 100,
      "hint": "Try SQL injection on the login form"
    }
  ],
  "scoring": {
    "total_points": 100,
    "passing_score": 100,
    "time_bonus": false,
    "penalty_for_hints": false
  },
  "narrative": {
    "scenario_background": "You've been hired to test the security of a web application.",
    "attacker_role": "Penetration Tester",
    "objectives": ["Find and exploit SQL injection", "Extract the admin password"],
    "success_criteria": "Capture the flag stored in the database"
  }
}
```

## Example Complex Scenario (Lateral Movement)

```json
{
  "metadata": {
    "name": "Corporate Network Pivot",
    "description": "Exploit a web server and pivot to internal database",
    "author": "CyberRange Team",
    "version": "1.0.0",
    "difficulty": "medium",
    "estimated_time_minutes": 60,
    "tags": ["web", "pivot", "lateral-movement", "database"],
    "learning_objectives": [
      "Exploit web vulnerabilities",
      "Perform lateral movement",
      "Access internal services"
    ]
  },
  "networks": [
    {
      "id": "net_dmz",
      "name": "dmz",
      "type": "public",
      "subnet": "172.20.0.0/24"
    },
    {
      "id": "net_internal",
      "name": "internal",
      "type": "isolated",
      "subnet": "172.20.1.0/24"
    }
  ],
  "hosts": [
    {
      "id": "host_attacker",
      "name": "attacker",
      "type": "attacker",
      "base_image": "kalilinux/kali-rolling",
      "networks": [{"network_id": "net_dmz", "ip_address": "172.20.0.5"}],
      "resources": {"cpu_limit": "2.0", "memory_limit": "2g"},
      "services": [],
      "vulnerabilities": [],
      "flags": []
    },
    {
      "id": "host_web",
      "name": "webserver",
      "type": "web",
      "base_image": "ubuntu:22.04",
      "networks": [
        {"network_id": "net_dmz", "ip_address": "172.20.0.10"},
        {"network_id": "net_internal", "ip_address": "172.20.1.10"}
      ],
      "resources": {"cpu_limit": "1.0", "memory_limit": "1g"},
      "services": ["svc_nginx"],
      "vulnerabilities": ["vuln_ssrf", "vuln_exposed_creds"],
      "flags": ["flag_web"]
    },
    {
      "id": "host_db",
      "name": "database",
      "type": "db",
      "base_image": "mysql:8.0",
      "networks": [{"network_id": "net_internal", "ip_address": "172.20.1.20"}],
      "resources": {"cpu_limit": "1.0", "memory_limit": "1g"},
      "services": ["svc_mysql"],
      "vulnerabilities": ["vuln_weak_db_password"],
      "flags": ["flag_db"]
    }
  ],
  "services": [
    {
      "id": "svc_nginx",
      "name": "nginx_web_server",
      "type": "nginx",
      "version": "1.22",
      "ports": [{"internal": 80, "external": 8080, "protocol": "tcp"}],
      "config": {}
    },
    {
      "id": "svc_mysql",
      "name": "mysql_database",
      "type": "mysql",
      "version": "8.0",
      "ports": [{"internal": 3306, "protocol": "tcp"}],
      "config": {
        "credentials": [{"username": "root", "password": "password123", "role": "admin"}]
      }
    }
  ],
  "vulnerabilities": [
    {
      "id": "vuln_ssrf",
      "name": "SSRF in Image Proxy",
      "type": "ssrf",
      "severity": "high",
      "description": "The web app has an SSRF vulnerability in the image proxy endpoint",
      "affected_service": "svc_nginx",
      "setup": {
        "module": "modules/ssrf_proxy.sh",
        "parameters": {"endpoint": "/proxy"}
      }
    },
    {
      "id": "vuln_exposed_creds",
      "name": "Exposed Database Credentials",
      "type": "misconfiguration",
      "severity": "medium",
      "description": "Database credentials are stored in a readable config file",
      "affected_service": "svc_nginx",
      "setup": {
        "module": "modules/exposed_config.sh",
        "parameters": {"file_path": "/var/www/config.php"}
      }
    },
    {
      "id": "vuln_weak_db_password",
      "name": "Weak Database Password",
      "type": "weak_password",
      "severity": "medium",
      "description": "Database uses a weak password",
      "affected_service": "svc_mysql",
      "setup": {
        "module": "modules/weak_mysql_password.sh",
        "parameters": {}
      }
    }
  ],
  "flags": [
    {
      "id": "flag_web",
      "name": "Web Server Flag",
      "value": "FLAG{ssrf_t0_1nt3rn4l}",
      "placement": {
        "type": "file",
        "host_id": "host_web",
        "details": {"path": "/var/www/flag.txt"}
      },
      "points": 40,
      "hint": "Look for misconfigurations in the web application"
    },
    {
      "id": "flag_db",
      "name": "Database Flag",
      "value": "FLAG{l4t3r4l_m0v3m3nt_c0mpl3t3}",
      "placement": {
        "type": "db_row",
        "host_id": "host_db",
        "details": {
          "table": "secrets",
          "query": "SELECT flag FROM secrets WHERE id=1"
        }
      },
      "points": 60,
      "hint": "Pivot from the web server to the internal network"
    }
  ],
  "scoring": {
    "total_points": 100,
    "passing_score": 80,
    "time_bonus": true,
    "penalty_for_hints": true
  },
  "narrative": {
    "scenario_background": "A company's web server is exposed to the internet. Your goal is to compromise it and pivot to the internal database server.",
    "attacker_role": "Red Team Operator",
    "objectives": [
      "Exploit the web server",
      "Find credentials for lateral movement",
      "Access the internal database",
      "Extract the final flag"
    ],
    "success_criteria": "Capture both flags"
  }
}
```

## Notes

- Use templates in flag values: `{random_uuid}`, `{random_hex_8}`, `{timestamp}`
- Resource limits follow Docker conventions: `"512m"`, `"1g"`, `"0.5"` CPU cores
- Custom modules are bash/python scripts that accept parameters via environment variables
- All paths are relative to container filesystem, not host
