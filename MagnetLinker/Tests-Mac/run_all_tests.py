#!/usr/bin/env python3
"""Run all tests and display comprehensive summary."""

import sys
import subprocess
import os
from pathlib import Path

def run_test_suite(test_file, suite_name):
    """Run a test suite and capture results."""
    print(f"\n{'='*70}")
    print(f"  {suite_name}")
    print(f"{'='*70}\n")
    
    # run tests with cwd set to project root directory dynamically
    project_root = Path(__file__).resolve().parent.parent
    env = os.environ.copy()
    # ensure project modules are importable
    env_py = env.get("PYTHONPATH", "")
    if env_py:
        env["PYTHONPATH"] = str(project_root) + ":" + env_py
    else:
        env["PYTHONPATH"] = str(project_root)
    result = subprocess.run([sys.executable, test_file], cwd=str(project_root), env=env)
    return result.returncode == 0


def main():
    """Run all test suites."""
    # ensure project root is known
    project_root = Path(__file__).resolve().parent.parent
    print("\n" + "="*70)
    print("  MAGNETLINKER - COMPREHENSIVE TEST SUITE")
    print("="*70)
    
    # tests are located relative to project root (macOS folder)
    test_suites = [
        (str(project_root / "Tests-Mac" / "test_comprehensive.py"), "1. Core Features Tests (23 tests)"),
        (str(project_root / "Tests-Mac" / "test_ui_integration.py"), "2. UI & Integration Tests (18 tests)"),
    ]
    
    results = {}
    total_tests = 0
    
    for test_file, suite_name in test_suites:
        success = run_test_suite(test_file, suite_name)
        results[suite_name] = success
        
        if "23 tests" in suite_name:
            total_tests += 23
        elif "18 tests" in suite_name:
            total_tests += 18
    
    # Final summary
    print("\n" + "="*70)
    print("  FINAL TEST SUMMARY")
    print("="*70)
    
    all_passed = all(results.values())
    
    print(f"\nTotal Test Suites: {len(results)}")
    print(f"Total Tests: {total_tests}")
    
    for suite_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {suite_name}: {status}")
    
    print("\n" + "="*70)
    
    if all_passed:
        print("  ✅ ALL TEST SUITES PASSED! - Ready for Production")
        print("\nTest Coverage:")
        print("  ✓ Magnet link detection and processing")
        print("  ✓ Settings validation (URLs, directories, cache duration)")
        print("  ✓ Settings persistence (cache manager, API client)")
        print("  ✓ Clipboard monitoring toggle")
        print("  ✓ Content type selection and caching")
        print("  ✓ Credentials management")
        print("  ✓ Menu bar app creation")
        print("  ✓ Sidebar navigation and sections")
        print("  ✓ Action buttons (Test Connection, Clear Credentials)")
        print("  ✓ Error handling and notifications")
    else:
        print("  ❌ SOME TEST SUITES FAILED - Review errors above")
        return 1
    
    print("\n" + "="*70 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
