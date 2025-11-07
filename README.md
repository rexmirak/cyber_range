# Cyber Range Scenario Deployer

> Automated cyber range lab deployment from JSON scenarios with LLM-powered authoring and guidance

## Overview

The Cyber Range Scenario Deployer is a local-first tool that takes scenario definitions in JSON format and automatically provisions complete penetration testing labs using Docker containers. It includes optional LLM-powered assistance for scenario authoring and in-lab guidance.

## Features

- 🎯 **Scenario-as-Code:** Define entire labs in structured JSON
- 🤖 **LLM-Assisted Authoring:** Generate scenarios from natural language descriptions
- 🐳 **Docker-Based:** Lightweight containers for rapid deployment
- 🔒 **Container-Friendly Vulnerabilities:** Web, service, and credential-based exploits
- 🚀 **Lateral Movement:** Multi-network topologies for realistic pivoting scenarios
- 🏁 **Flag System:** Automated flag placement and verification
- 📊 **PDF Reports:** Comprehensive completion proofs with timestamps
- 🔐 **Local & Private:** All LLM processing runs locally via Ollama

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface (CLI)                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ LLM Adapter  │  │ Orchestrator │  │ Flag Service │      │
│  │  (Ollama)    │  │   (Python)   │  │   (Python)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         v                  v                  v              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Scenario   │  │   Docker     │  │     PDF      │      │
│  │  Validator   │  │  Management  │  │   Reports    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              v
        ┌────────────────────────────────────────┐
        │         Docker Infrastructure          │
        │  ┌────────┐  ┌────────┐  ┌────────┐  │
        │  │  Web   │  │   DB   │  │ Attacker│ │
        │  │Container│  │Container│ │Container│ │
        │  └────────┘  └────────┘  └────────┘  │
        └────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Docker installed and running
- Ollama installed with llama3.2:latest
- Python 3.9+
- Running in a VM (recommended for isolation)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd cyber_range

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Install Ollama and pull model
ollama pull llama3.2:latest

# Verify installation
python -m pytest tests/ -v -m "not integration"  # Should pass all 96 unit tests
```

### Usage

#### 1. Create a Scenario (LLM-Assisted)

```bash
# Start interactive authoring
./cyber_range author

# Example prompt:
# "Create a web server with SQL injection and a database with weak password"
```

#### 2. Deploy a Lab

```bash
# Deploy from scenario file
./cyber_range deploy examples/sqli_basic.json

# Deploy and start guidance
./cyber_range deploy examples/lateral_movement.json --guide
```

#### 3. Interact with the Lab

```bash
# Get lab info
./cyber_range info

# Submit a flag
./cyber_range submit "FLAG{sql_1nj3ct10n_m4st3r}"

# Get a hint
./cyber_range hint
```

#### 4. Teardown and Report

```bash
# Generate completion report and teardown
./cyber_range teardown --report report.pdf
```

## Scenario Structure

Scenarios are defined in JSON with the following main sections:

- **metadata**: Name, description, difficulty, learning objectives
- **networks**: Docker networks with subnets and isolation levels
- **hosts**: Containers with services, vulnerabilities, and flags
- **services**: Service configurations (web servers, databases, etc.)
- **vulnerabilities**: Exploitable weaknesses to inject
- **flags**: Capture-the-flag objectives with placement details
- **scoring**: Point system and completion criteria
- **narrative**: Scenario background and objectives

See [docs/scenario_schema.md](docs/scenario_schema.md) for complete documentation.

## Example Scenarios

### SQL Injection Basic (Easy)

A simple web application with a SQL injection vulnerability. Perfect for beginners.

```bash
./cyber_range deploy examples/sqli_basic.json
```

**Learning Objectives:**
- Identify SQL injection vulnerabilities
- Extract data using SQL injection
- Understand basic web security testing

### Corporate Network Pivot (Medium)

A multi-tier environment requiring lateral movement from a DMZ web server to an internal database.

```bash
./cyber_range deploy examples/lateral_movement.json
```

**Learning Objectives:**
- Exploit web vulnerabilities (SSRF)
- Perform lateral movement
- Access internal services
- Extract credentials

## Supported Vulnerabilities

- Weak/default passwords
- Outdated software versions
- Service misconfigurations
- Exposed services
- Vulnerable web applications
- Directory traversal
- SQL injection
- Command injection
- Server-side request forgery (SSRF)
- Lateral movement opportunities

## LLM Features

### Scenario Authoring

The LLM can help create scenario JSON from natural language:

```
You: "I want a lab with a vulnerable WordPress site and a MySQL database"

LLM: [Generates valid JSON scenario with appropriate services and vulnerabilities]
```

### In-Lab Guidance

During the lab, the LLM provides tiered hints:

- **Tier 0:** Gentle nudge (restate objective)
- **Tier 1:** Directional clue (suggest service or area)
- **Tier 2:** Concrete technique (specific attack method)
- **Tier 3:** Step-by-step (detailed walkthrough)

### Learning Explanations

After completing a lab, get detailed explanations:

- What vulnerability was exploited
- Why it was vulnerable
- How to remediate it
- Real-world implications

## Project Structure

```
cyber_range/
├── docs/                       # Documentation
│   ├── planning_summary.md     # Phase 1 architecture
│   ├── scenario_schema.md      # Complete schema docs
│   ├── phase2_llm.md           # Phase 2 implementation
│   ├── phase2_test_results.md  # Phase 2 test results
│   └── testing_guide.md        # Testing guide
├── examples/                   # Example scenarios
│   ├── sqli_basic.json         # SQL injection lab
│   ├── lateral_movement.json   # Multi-network pivot
│   └── llm_usage.py            # LLM API examples
├── schema/                     # JSON Schema definitions
│   └── scenario.schema.json    # Validation schema
├── src/                        # Source code
│   └── llm/                    # LLM integration (Phase 2) ✅
│       ├── adapter.py          # Ollama adapter (359 LOC)
│       ├── prompts.py          # Prompt engineering (445 LOC)
│       ├── rag.py              # RAG pipeline (306 LOC)
│       ├── tools.py            # Tool registry (269 LOC)
│       └── integration.py      # High-level API (247 LOC)
├── tests/                      # Test suite (Phase 2) ✅
│   ├── test_llm_adapter.py     # Adapter tests (19 tests)
│   ├── test_prompts.py         # Prompt tests (27 tests)
│   ├── test_rag.py             # RAG tests (22 tests)
│   ├── test_tools.py           # Tool tests (28 tests)
│   └── test_integration.py     # Integration tests (6 tests)
├── test.sh                     # Test runner script
├── run_tests.py                # Python test runner
└── requirements.txt            # Python dependencies
```

## Testing

### Run Tests

```bash
# All unit tests (no Ollama required)
./test.sh unit         # or just ./test.sh

# With coverage report
./test.sh coverage

# Integration tests (requires Ollama)
./test.sh integration

# All tests
./test.sh all
```

### Test Results (Phase 2)

✅ **96/96 unit tests passing** (100% pass rate)
- 19 adapter tests (Ollama connection, generation, JSON extraction)
- 27 prompt tests (system prompts, CoT, few-shot, sanitization)
- 22 RAG tests (embeddings, search, indexing)
- 28 tool tests (GetDocs, GetState, ValidateJSON, DiffJSON)

See `docs/phase2_test_results.md` for detailed results.

## Development Phases

- ✅ **Phase 1:** Planning and schema design
- ✅ **Phase 2:** LLM APIs, tools, and prompting (1,850 LOC, 96 tests passing)
- ⏳ **Phase 3:** Orchestrator implementation (validator, planner, provisioner)
- ⏳ **Phase 4:** Phase 3 unit tests
- ⏳ **Phase 5:** Integration tests (end-to-end)
- ⏳ **Phase 6:** Documentation and demo
- ⏳ **Phase 7:** Security and resource guardrails

## Contributing

This is a portfolio project. Contributions, suggestions, and feedback are welcome!

## Security Notice

⚠️ **Always run labs in an isolated VM.** The vulnerabilities deployed are real and can compromise your host system if not properly isolated.

## License

[To be determined]

## Author

Karim - [Your contact/portfolio info]

---

**Status:** Phase 1 Complete ✅  
**Next:** LLM integration and prompting system
