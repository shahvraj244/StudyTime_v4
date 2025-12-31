#!/usr/bin/env python3
"""
Complete system check for StudyTime backend
Works on Windows, Linux, and macOS
Run with: python run_checks.py
"""

import subprocess
import sys
import os
from pathlib import Path

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Disable colors on Windows unless using Windows Terminal
if os.name == 'nt' and not os.environ.get('WT_SESSION'):
    Colors.GREEN = Colors.RED = Colors.YELLOW = Colors.BLUE = Colors.BOLD = Colors.END = ''

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")

def print_section(text):
    print(f"\n{Colors.BOLD}{text}{Colors.END}")
    print("-" * len(text))

def print_check(name, status, message=""):
    symbol = "✓" if status else "✗"
    color = Colors.GREEN if status else Colors.RED
    print(f"{color}{symbol}{Colors.END} {name}")
    if message:
        print(f"  {message}")

def run_command(command, capture_output=True):
    """Run a command and return success status"""
    try:
        if capture_output:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(command, shell=True, timeout=10)
            return result.returncode == 0, "", ""
    except Exception as e:
        return False, "", str(e)

def check_python_import(module):
    """Check if a Python module can be imported"""
    try:
        __import__(module)
        return True
    except ImportError:
        return False

def main():
    print_header("StudyTime Backend - Complete System Check")
    
    checks_passed = 0
    checks_failed = 0
    
    # 1. Environment Checks
    print_section("1. Environment Checks")
    
    # Python version
    python_version = sys.version.split()[0]
    major, minor = map(int, python_version.split('.')[:2])
    python_ok = major == 3 and minor >= 8
    print_check(f"Python 3.8+", python_ok, f"Found: Python {python_version}")
    if python_ok:
        checks_passed += 1
    else:
        checks_failed += 1
    
    # pip
    pip_ok, _, _ = run_command("pip --version")
    print_check("pip installed", pip_ok)
    if pip_ok:
        checks_passed += 1
    else:
        checks_failed += 1
    
    # 2. Dependencies
    print_section("2. Dependencies")
    
    # requirements.txt
    req_file = Path("requirements.txt")
    req_ok = req_file.exists()
    print_check("requirements.txt exists", req_ok)
    if req_ok:
        checks_passed += 1
    else:
        checks_failed += 1
    
    # Key packages
    packages = {
        "FastAPI": "fastapi",
        "SQLAlchemy": "sqlalchemy",
        "Uvicorn": "uvicorn",
        "Pydantic": "pydantic"
    }
    
    for name, module in packages.items():
        installed = check_python_import(module)
        print_check(f"{name} installed", installed)
        if installed:
            checks_passed += 1
        else:
            checks_failed += 1
    
    # 3. File Structure
    print_section("3. File Structure")
    
    required_files = ["main.py", "database.py", "models.py", "scheduler.py"]
    
    for filename in required_files:
        exists = Path(filename).exists()
        print_check(f"{filename} exists", exists)
        if exists:
            checks_passed += 1
        else:
            checks_failed += 1
    
    # 4. Database Operations
    print_section("4. Database Operations")
    
    # Initialize database
    print(f"{Colors.BLUE}▶ Initializing database...{Colors.END}")
    db_init_ok, stdout, stderr = run_command("python database.py init")
    print_check("Database initialization", db_init_ok)
    if db_init_ok:
        checks_passed += 1
    else:
        checks_failed += 1
        if stderr:
            print(f"  Error: {stderr[:200]}")
    
    # Check connection
    db_check_ok, _, _ = run_command("python database.py check")
    print_check("Database connection", db_check_ok)
    if db_check_ok:
        checks_passed += 1
    else:
        checks_failed += 1
    
    # Get info
    db_info_ok, _, _ = run_command("python database.py info")
    print_check("Database info retrieval", db_info_ok)
    if db_info_ok:
        checks_passed += 1
    else:
        checks_failed += 1
    
    # 5. SQLAlchemy 2.0 Compatibility
    print_section("5. SQLAlchemy 2.0 Compatibility")
    
    if Path("verify_fix.py").exists():
        verify_ok, _, _ = run_command("python verify_fix.py")
        print_check("SQLAlchemy text() fix verified", verify_ok)
        if verify_ok:
            checks_passed += 1
        else:
            checks_failed += 1
    else:
        print(f"{Colors.YELLOW}⚠ verify_fix.py not found (skipping){Colors.END}")
    
    # 6. Code Syntax
    print_section("6. Code Syntax")
    
    for filename in required_files:
        if Path(filename).exists():
            syntax_ok, _, _ = run_command(f"python -m py_compile {filename}")
            print_check(f"{filename} syntax", syntax_ok)
            if syntax_ok:
                checks_passed += 1
            else:
                checks_failed += 1
    
    # Summary
    print_header("SUMMARY")
    
    print(f"{Colors.GREEN}✓ Passed: {checks_passed}{Colors.END}")
    if checks_failed > 0:
        print(f"{Colors.RED}✗ Failed: {checks_failed}{Colors.END}")
    else:
        print(f"{Colors.GREEN}✗ Failed: {checks_failed}{Colors.END}")
    
    print()
    
    if checks_failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 All checks passed! Your backend is ready!{Colors.END}\n")
        print("Next steps:")
        print("  1. Start the server:")
        print("     uvicorn main:app --reload\n")
        print("  2. Run tests (in another terminal):")
        print("     python test_backend.py\n")
        print("  3. View API docs:")
        print("     http://localhost:8000/docs\n")
    else:
        print(f"{Colors.RED}⚠ Some checks failed. Please review the errors above.{Colors.END}\n")
        print("Common fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Check Python version: python --version (need 3.8+)")
        print("  - Verify SQLAlchemy 2.0: pip install --upgrade sqlalchemy\n")
    
    print(f"{Colors.BLUE}{'=' * 60}{Colors.END}\n")
    
    return checks_failed

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Checks interrupted by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Error running checks: {e}{Colors.END}")
        sys.exit(1)