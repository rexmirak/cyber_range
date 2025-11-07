#!/usr/bin/env bash
# Quick test runner for Phase 2

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PROJECT_ROOT}/.venv/bin/python"

echo "═══════════════════════════════════════════════════════════"
echo "  Cyber Range - Phase 2 Test Suite"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Check if venv exists
if [ ! -f "$PYTHON" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Run: python -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Parse arguments
MODE="${1:-unit}"

case "$MODE" in
    unit)
        echo "Running unit tests only (no Ollama required)..."
        echo ""
        "$PYTHON" -m pytest tests/ -v -m "not integration" --tb=short
        ;;
    
    integration)
        echo "Running integration tests (requires Ollama)..."
        echo ""
        # Check if Ollama is running
        if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo "❌ Ollama is not running!"
            echo "   Start with: ollama serve"
            exit 1
        fi
        
        "$PYTHON" -m pytest tests/test_integration.py -v -s --tb=short
        ;;
    
    all)
        echo "Running all tests (requires Ollama)..."
        echo ""
        # Check Ollama
        if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo "⚠️  Ollama not running, will skip integration tests"
            "$PYTHON" -m pytest tests/ -v -m "not integration" --tb=short
        else
            "$PYTHON" -m pytest tests/ -v --tb=short
        fi
        ;;
    
    coverage)
        echo "Running tests with coverage report..."
        echo ""
        "$PYTHON" -m pytest tests/ -v -m "not integration" \
            --cov=src/llm \
            --cov-report=term-missing \
            --cov-report=html \
            --tb=short
        echo ""
        echo "✅ Coverage report generated: htmlcov/index.html"
        ;;
    
    fast)
        echo "Running fast tests only..."
        echo ""
        "$PYTHON" -m pytest tests/ -v -m "not integration and not slow" --tb=short
        ;;
    
    *)
        echo "Usage: $0 [unit|integration|all|coverage|fast]"
        echo ""
        echo "Modes:"
        echo "  unit        - Run unit tests only (default, no Ollama required)"
        echo "  integration - Run integration tests (requires Ollama)"
        echo "  all         - Run all tests (requires Ollama)"
        echo "  coverage    - Run with coverage report"
        echo "  fast        - Run fast tests only (skip slow tests)"
        echo ""
        echo "Examples:"
        echo "  $0              # Run unit tests"
        echo "  $0 integration  # Run integration tests"
        echo "  $0 coverage     # Run with coverage"
        exit 1
        ;;
esac

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  ✅ All tests passed!"
    echo "═══════════════════════════════════════════════════════════"
else
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  ❌ Some tests failed"
    echo "═══════════════════════════════════════════════════════════"
fi

exit $EXIT_CODE
