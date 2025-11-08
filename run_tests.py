#!/usr/bin/env python3
"""
Test Runner for Phase 2 LLM Components

Runs all unit tests for the LLM integration modules.
"""

import sys
import subprocess
from pathlib import Path


def check_dependencies():
    """Check if required test dependencies are installed"""
    try:
        import pytest  # noqa: F401
        return True
    except ImportError:
        print("❌ pytest not installed")
        print("\nInstall test dependencies:")
        print("  pip install -r requirements.txt")
        return False


def run_tests(verbose=True, coverage=False):
    """
    Run all tests
    
    Args:
        verbose: Show detailed output
        coverage: Generate coverage report
    """
    project_root = Path(__file__).parent.parent
    
    # Build pytest command
    # Use pytest from venv if available
    import os
    venv_pytest = os.path.join(os.path.dirname(sys.executable), 'pytest')
    pytest_cmd = venv_pytest if os.path.exists(venv_pytest) else 'pytest'

    cmd = [pytest_cmd]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=src/llm", "--cov-report=term-missing"])
    
    # Add test directory
    cmd.append("tests/")
    
    print("=" * 60)
    print("Running Phase 2 LLM Tests")
    print("=" * 60)
    print()
    
    # Run tests
    result = subprocess.run(cmd, cwd=project_root)
    
    return result.returncode


def run_specific_module(module_name):
    """
    Run tests for a specific module
    
    Args:
        module_name: Name of module (adapter, rag, prompts, tools)
    """
    test_file = f"tests/test_{module_name}.py"
    
    print(f"Running tests for {module_name}...")
    result = subprocess.run(["pytest", "-v", test_file])
    
    return result.returncode


def main():
    """Main test runner"""
    if not check_dependencies():
        return 1
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--coverage":
            return run_tests(verbose=True, coverage=True)
        elif sys.argv[1] in ["adapter", "rag", "prompts", "tools"]:
            return run_specific_module(sys.argv[1])
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python run_tests.py              Run all tests")
            print("  python run_tests.py --coverage   Run with coverage report")
            print("  python run_tests.py adapter      Run adapter tests only")
            print("  python run_tests.py rag          Run RAG tests only")
            print("  python run_tests.py prompts      Run prompts tests only")
            print("  python run_tests.py tools        Run tools tests only")
            return 0
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
            return 1
    
    # Run all tests
    return run_tests(verbose=True, coverage=False)


if __name__ == "__main__":
    sys.exit(main())
