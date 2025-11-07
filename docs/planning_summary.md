# Cyber Range Scenario Deployer - Phase 1 Planning Summary

## Project Overview

A local-first cyber range scenario deployer that takes JSON scenario definitions and automatically provisions Docker-based labs with vulnerabilities, flags, and optional LLM-powered guidance.

## Architecture Summary

### Core Components

1. **Orchestrator (Python)**
   - Parses and validates scenario JSON
   - Plans deployment graph and dependency order
   - Calls bash scripts for Docker/network operations
   - Tracks lab state, user actions, and flag submissions
   - Generates PDF completion reports

2. **LLM Adapter (Python + Ollama)**
   - Scenario authoring assistant (JSON generation)
   - Repair loop for schema violations
   - In-lab guidance system (tiered hints)
   - Explanation engine for learning objectives

3. **Vulnerability Modules (Bash/Python)**
   - Curated scripts for container-compatible vulnerabilities
   - Parameterized setup with templates
   - Support for web, service, credential, and lateral movement attacks

4. **Network Management (Bash + Docker)**
   - Docker bridge and custom bridge networks
   - IP assignment and routing
   - Inter-container connectivity for lateral movement

5. **Flag Service (Python)**
   - Flag placement (file, env, service_response, db_row)
   - Submission verification
   - Scoring engine with optional time bonuses

6. **PDF Report Generator (Python + reportlab/fpdf)**
   - Captures initial prompt and scenario JSON
   - Logs user actions with timestamps
   - Records flag submissions and scoring
   - Exports comprehensive completion proof

## Technology Stack

- **Language:** Python (primary), Bash (Docker/network commands)
- **Containerization:** Docker (containers only, no VMs in MVP)
- **LLM Runtime:** Ollama with llama3.2:latest
- **Validation:** JSON Schema + custom policy engine
- **Reporting:** Python reportlab or fpdf
- **Networking:** Docker bridge networks
- **Storage:** SQLite for lab state and session logs

## Supported Features (MVP)

### Container Types
- `attacker`: Kali Linux with pre-installed tools
- `victim`: Generic vulnerable targets
- `web`: Web servers (nginx, apache, flask, node)
- `db`: Databases (mysql, postgres)
- `ftp`: FTP servers (vsftpd)
- `smb`: Samba file servers
- `custom`: User-defined Dockerfile

### Network Types
- `bridge`: Default Docker bridge
- `custom_bridge`: User-defined Docker network with custom subnet
- `isolated`: No external access except from attacker
- `public`: Exposed to host for testing

### Vulnerability Types (Container-Compatible)
- `weak_password`: Weak/default credentials
- `outdated_software`: Known vulnerable versions
- `misconfiguration`: Insecure service configs
- `default_creds`: Default admin accounts
- `exposed_service`: Unnecessary exposed ports/services
- `vulnerable_webapp`: Intentionally vulnerable web apps
- `directory_traversal`: Path traversal vulnerabilities
- `sql_injection`: SQLi vulnerabilities
- `command_injection`: OS command injection
- `ssrf`: Server-side request forgery
- `lateral_movement`: Pivot opportunities between containers

### Flag Placement Types
- `file`: Store in a file at specified path
- `env`: Set as environment variable
- `service_response`: Return from web endpoint or service
- `db_row`: Insert into database table

### Scoring & Proof
- Point-based scoring system
- Optional time bonuses
- Optional hint penalties
- PDF completion report with:
  - Initial prompt and scenario JSON
  - Lab topology and configuration
  - User actions with timestamps
  - Flag submissions and scores
  - Total time and final score

## User Flow

1. **Authoring**
   - User describes scenario via CLI/LLM chat
   - LLM outputs validated JSON scenario
   - User reviews and optionally edits

2. **Deployment**
   - Orchestrator validates JSON
   - Creates Docker networks
   - Spins up containers with services
   - Injects vulnerabilities
   - Places flags

3. **Lab Experience**
   - User receives IP addresses and access info
   - Optional LLM guide for hints and troubleshooting
   - User attacks, pivots, solves challenges
   - Submits flags via CLI

4. **Completion**
   - Orchestrator verifies flags
   - Generates PDF report
   - User tears down lab
   - Exports completion proof

## Local Limitations & Requirements

- **Docker Required:** Must be installed and running
- **Ollama Required:** For LLM features (llama3.2:latest)
- **VM Isolation:** User should run lab in a VM for host safety
- **No Kernel Exploits:** Container limitations exclude certain privilege escalation vectors
- **Resource Limits:** CPU/RAM/disk quotas enforced per container
- **Offline Operation:** All LLM processing is local; no cloud dependencies

## Enums Reference

### Difficulty Levels
- `easy`: Beginner-friendly, straightforward exploitation
- `medium`: Multiple steps, requires intermediate knowledge
- `hard`: Complex chains, advanced techniques

### Service Types
- `nginx`, `apache`, `flask`, `node` (web servers)
- `mysql`, `postgres` (databases)
- `vsftpd` (FTP)
- `openssh` (SSH)
- `samba` (SMB)
- `custom` (user-defined)

### Severity Levels
- `low`: Minor information disclosure
- `medium`: Partial compromise or data exposure
- `high`: Full system compromise or significant data breach
- `critical`: Complete network compromise or critical data loss

## Example Scenarios

### 1. SQL Injection Basic (Easy)
- Single web server with SQLi vulnerability
- Extract admin password from database
- 30 minutes, 100 points
- File: `examples/sqli_basic.json`

### 2. Corporate Network Pivot (Medium)
- DMZ web server + internal database
- SSRF vulnerability + exposed credentials
- Lateral movement required
- 60 minutes, 100 points (40 + 60)
- File: `examples/lateral_movement.json`

## Project Phases

### Phase 1: Planning ✅
- Architecture finalized
- Enums and schema defined
- MVP scope documented
- Example scenarios created

### Phase 2: LLM APIs, Tools, and Prompting
- Implement Ollama adapter
- Design APIs for authoring, repair, guidance
- Engineer prompts with CoT and few-shot examples
- Build local RAG pipeline

### Phase 3: Orchestrator
- JSON parser and validator
- Deployment planner
- Docker/network provisioning
- Vulnerability injection
- Flag placement and verification
- Session logging
- PDF report generation

### Phase 4: Unit Test Development and Running
- Test LLM adapter
- Test validator and schema enforcement
- Test orchestrator modules
- Test PDF generation

### Phase 5: Integration Test Development and Running
- End-to-end scenario tests
- Simulated user actions
- Flag submission validation
- Report completeness checks

### Phase 6: Documentation and Demo
- README and usage guide
- Developer documentation
- Video/transcript demo

### Phase 7: Security and Resource Guardrails
- Resource limits enforcement
- Sandboxing and isolation checks
- Sensitive data redaction
- Security audit

## Key Design Decisions

1. **JSON over YAML:** Easier for LLM output, better validation tooling
2. **Docker-only MVP:** Simpler than VMs, sufficient for most web/service vulns
3. **Bash for Commands:** Direct Docker/network operations via subprocess
4. **Python for Logic:** Schema validation, orchestration, reporting
5. **Local LLM (Ollama):** Privacy, offline operation, no API costs
6. **PDF Reports:** Professional, portable proof of completion
7. **Lateral Movement:** Multi-network topology for realistic scenarios

## Next Steps

- Begin Phase 2: Implement LLM adapter and prompting system
- Create Ollama integration module
- Design system prompts and few-shot examples
- Build scenario authoring and repair loops

## Success Criteria

- User can describe a scenario and get valid JSON
- Orchestrator deploys containers with vulnerabilities and flags
- User can attack lab and submit flags
- PDF report captures complete session
- All tests pass (unit + integration)
- Documentation is clear and complete
- Demo showcases end-to-end workflow

---

**Date:** November 7, 2025  
**Status:** Phase 1 Complete ✅  
**Next Phase:** LLM APIs, Tools, and Prompting
