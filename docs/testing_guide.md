# Testing Guide - Phase 2 LLM Components

## Overview

This guide covers testing the LLM integration layer including unit tests and integration tests.

## Prerequisites

1. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ollama** (for integration tests)
   - Install: https://ollama.ai
   - Start server: `ollama serve`
   - Pull model: `ollama pull llama3.2:latest`

## Test Structure

```
tests/
├── __init__.py
├── test_llm_adapter.py      # Ollama adapter tests (unit)
├── test_rag.py               # RAG pipeline tests (unit)
├── test_prompts.py           # Prompt builders tests (unit)
├── test_tools.py             # Tool registry tests (unit)
└── test_integration.py       # End-to-end tests (integration)
```

## Running Tests

### All Tests

```bash
# Run all unit tests
python run_tests.py

# With coverage report
python run_tests.py --coverage
```

### Specific Module Tests

```bash
# Test adapter only
python run_tests.py adapter

# Test RAG only
python run_tests.py rag

# Test prompts only
python run_tests.py prompts

# Test tools only
python run_tests.py tools
```

### Integration Tests

```bash
# Run integration tests (requires Ollama)
pytest tests/test_integration.py -v -s

# Skip slow tests
pytest tests/test_integration.py -v -m "not slow"
```

### Using pytest Directly

```bash
# All tests with verbose output
pytest -v

# Specific test file
pytest tests/test_llm_adapter.py -v

# Specific test class
pytest tests/test_llm_adapter.py::TestOllamaAdapter -v

# Specific test method
pytest tests/test_llm_adapter.py::TestOllamaAdapter::test_generate_basic -v

# With coverage
pytest --cov=src/llm --cov-report=html

# Skip integration tests
pytest -m "not integration"

# Only integration tests
pytest -m "integration"
```

## Test Categories

### Unit Tests (No External Dependencies)

**test_llm_adapter.py**
- Ollama connection verification (mocked)
- Text generation (mocked)
- JSON extraction
- Error handling
- Configuration management

**test_rag.py**
- Document indexing
- Vector search
- Embedding computation
- Scenario indexing
- Knowledge base indexing

**test_prompts.py**
- Prompt builders
- System prompts validation
- Few-shot examples
- Scenario sanitization
- Chain-of-thought templates

**test_tools.py**
- Tool execution
- Tool registry management
- Result handling
- Error conditions

### Integration Tests (Requires Ollama)

**test_integration.py**
- Full scenario generation workflow
- Hint generation at all tiers
- Concept explanations
- RAG-enhanced features
- End-to-end LLM integration

## Test Coverage

Expected coverage areas:

| Module | Lines | Coverage Target |
|--------|-------|----------------|
| adapter.py | 359 | >90% |
| prompts.py | 445 | >85% |
| rag.py | 306 | >85% |
| tools.py | 269 | >90% |
| integration.py | 247 | >75% |

## Common Issues

### 1. Import Errors

**Problem:** `ModuleNotFoundError: No module named 'src'`

**Solution:**
```bash
# Run from project root
cd /Users/karim/Desktop/projects/cyber_range
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### 2. Ollama Not Running

**Problem:** `RuntimeError: Cannot connect to Ollama`

**Solution:**
```bash
# Start Ollama server
ollama serve

# In another terminal, verify
curl http://localhost:11434/api/tags
```

### 3. Model Not Available

**Problem:** `RuntimeError: Model llama3.2:latest not found`

**Solution:**
```bash
ollama pull llama3.2:latest
```

### 4. Sentence Transformers Not Installed

**Problem:** `ModuleNotFoundError: No module named 'sentence_transformers'`

**Solution:**
```bash
pip install sentence-transformers
```

### 5. Test Database Errors

**Problem:** SQLite database locked or permission issues

**Solution:** Tests use temporary databases; ensure `/tmp` is writable

## Test Data

### Mock Data Structure

```python
# Example scenario for testing
test_scenario = {
    "metadata": {
        "name": "Test Lab",
        "difficulty": "easy",
        "version": "1.0.0",
    },
    "networks": [...],
    "hosts": [...],
    "flags": [...]
}
```

### Fixtures Available

- `temp_db`: Temporary database path
- `rag`: RAG instance with temp database
- `llm`: LLM integration instance
- `schema`: Loaded JSON schema
- `enums`: Available enum values

## Writing New Tests

### Unit Test Template

```python
import pytest
from src.llm.your_module import YourClass

class TestYourClass:
    """Test suite for YourClass"""
    
    def test_basic_functionality(self):
        """Test basic feature"""
        obj = YourClass()
        result = obj.method()
        assert result == expected_value
    
    def test_error_handling(self):
        """Test error conditions"""
        obj = YourClass()
        with pytest.raises(ValueError):
            obj.method(invalid_input)
```

### Integration Test Template

```python
import pytest

@pytest.mark.integration
@pytest.mark.slow  # For tests that take >5 seconds
class TestIntegration:
    """Integration test suite"""
    
    def test_full_workflow(self):
        """Test complete workflow"""
        # Setup
        # Execute
        # Verify
        pass
```

## Continuous Integration

### GitHub Actions (Future)

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run unit tests
        run: pytest -m "not integration" --cov=src/llm
```

## Test Metrics

### Current Status (Phase 2)

- **Total Test Files:** 5
- **Total Test Cases:** ~100+
- **Unit Tests:** ~85
- **Integration Tests:** ~15
- **Mock Coverage:** High (all external dependencies mocked)

### Running Metrics

```bash
# Count tests
pytest --collect-only | grep "test session starts"

# Coverage summary
pytest --cov=src/llm --cov-report=term-missing

# Test duration
pytest --durations=10
```

## Best Practices

1. **Isolation:** Each test should be independent
2. **Mocking:** Mock external dependencies (Ollama, file system)
3. **Fixtures:** Use pytest fixtures for common setup
4. **Naming:** Use descriptive test names (test_feature_condition_outcome)
5. **Documentation:** Add docstrings to test classes and methods
6. **Fast Tests:** Keep unit tests fast (<1s each)
7. **Integration Tags:** Mark slow/integration tests appropriately

## Debugging Tests

### Verbose Output

```bash
# Show print statements
pytest -v -s

# Show full diffs
pytest -vv

# Stop on first failure
pytest -x

# Run specific failed test
pytest tests/test_llm_adapter.py::TestOllamaAdapter::test_generate_basic -v
```

### Using pdb

```python
def test_debug_example():
    import pdb; pdb.set_trace()
    # Your test code
```

### Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Performance Testing

### Timing Tests

```bash
# Show slowest tests
pytest --durations=10

# Profile test execution
pytest --profile
```

### Load Testing (LLM)

```python
@pytest.mark.slow
def test_concurrent_requests():
    """Test handling multiple concurrent LLM requests"""
    # Not yet implemented
    pass
```

## Next Steps

After Phase 2 tests pass:
1. Integrate with validator (Phase 3)
2. Add orchestrator tests
3. Add end-to-end deployment tests
4. Set up CI/CD pipeline

## Getting Help

- Review test output carefully
- Check fixture setup
- Verify Ollama is running for integration tests
- Ensure PYTHONPATH includes project root
- Check requirements.txt dependencies installed

---

**Last Updated:** Phase 2 Complete  
**Test Status:** Unit tests ready, integration tests require Ollama
