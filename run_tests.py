#!/usr/bin/env python
"""
Test runner script for Chatify
Run all tests or specific test categories
"""
import sys
import pytest
import argparse


def main():
    """Run tests with specified options"""
    parser = argparse.ArgumentParser(description='Run Chatify tests')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--slow', action='store_true', help='Include slow tests')
    parser.add_argument('--auth', action='store_true', help='Run only auth tests')
    parser.add_argument('--chat', action='store_true', help='Run only chat tests')
    parser.add_argument('--group', action='store_true', help='Run only group tests')
    parser.add_argument('--file', type=str, help='Run specific test file')
    
    args = parser.parse_args()
    
    # Build pytest arguments
    pytest_args = ['tests/']
    
    if args.verbose:
        pytest_args.append('-v')
    
    if args.coverage:
        pytest_args.extend(['--cov=app', '--cov-report=html', '--cov-report=term'])
    
    if args.auth:
        pytest_args.append('tests/test_auth.py')
    elif args.chat:
        pytest_args.append('tests/test_chat.py')
    elif args.group:
        pytest_args.append('tests/test_groups.py')
    elif args.file:
        pytest_args = [f'tests/{args.file}']
    
    if not args.slow:
        pytest_args.extend(['-m', 'not slow'])
    
    # Run tests
    print("\n" + "="*70)
    print("Running Chatify Test Suite")
    print("="*70 + "\n")
    
    exit_code = pytest.main(pytest_args)
    
    print("\n" + "="*70)
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    print("="*70 + "\n")
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
