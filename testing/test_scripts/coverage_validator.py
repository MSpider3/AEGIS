import os
import subprocess
import sys
import json

BASE_TEMP = "testing"
VENV_PYTHON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "venv", "bin", "python"))
VENV_PIP = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "venv", "bin", "pip"))

def install_coverage_deps():
    print("[INFO] Ensuring coverage dependencies (pytest-cov, coverage) are installed...")
    try:
        subprocess.run([VENV_PIP, "install", "pytest-cov", "coverage"], check=True)
    except Exception as e:
        print(f"[WARN] Failed to install coverage dependencies: {e}. Attempting to run coverage check anyway.")

def run_coverage():
    install_coverage_deps()
    
    print("[INFO] Running test suite with coverage collection...")
    # We run pytest on functional tests
    test_file = os.path.join(BASE_TEMP, "test_scripts", "run_functional_tests.py")
    
    # Run pytest with coverage flags
    cov_json_path = os.path.join(BASE_TEMP, "coverage.json")
    cmd = [
        VENV_PYTHON, "-m", "pytest",
        "--cov=src",
        "--cov-branch",
        f"--cov-report=json:{cov_json_path}",
        test_file
    ]
    
    env = os.environ.copy()
    env["COVERAGE_FILE"] = os.path.join(BASE_TEMP, ".coverage")
    
    try:
        res = subprocess.run(cmd, env=env, capture_output=True, text=True)
        print(res.stdout)
        if res.returncode != 0:
            print("[WARN] Some tests failed under coverage run.")
            print(res.stderr)
    except Exception as e:
        print(f"[ERROR] Failed to execute coverage: {e}")
        return False, 0.0, 0.0

    if not os.path.exists(cov_json_path):
        print("[ERROR] coverage.json was not generated.")
        return False, 0.0, 0.0
        
    try:
        with open(cov_json_path, "r") as f:
            cov_data = json.load(f)

            
        totals = cov_data.get("totals", {})
        total_coverage = totals.get("percent_covered", 0.0)
        # In coverage.json, branch coverage is stored if enabled
        # Let's extract branch coverage if present
        covered_branches = totals.get("covered_branches", 0)
        num_branches = totals.get("num_branches", 0)
        branch_coverage = (covered_branches / num_branches * 100.0) if num_branches > 0 else 100.0
        
        print(f"\n--- Coverage Results ---")
        print(f"  Total Code Coverage: {total_coverage:.2f}% (Target: 90.00%)")
        print(f"  Branch Coverage: {branch_coverage:.2f}% (Target: 80.00%)")
        
        # Enforce requirements
        passed = True
        reasons = []
        if total_coverage < 90.0:
            passed = False
            reasons.append(f"Code coverage {total_coverage:.2f}% is below 90% target.")
        if branch_coverage < 80.0:
            passed = False
            reasons.append(f"Branch coverage {branch_coverage:.2f}% is below 80% target.")
            
        # Write report to logs/coverage_report.json
        report_path = os.path.join(BASE_TEMP, "logs", "coverage_report.json")
        with open(report_path, "w") as rf:
            json.dump({
                "code_coverage_percent": total_coverage,
                "branch_coverage_percent": branch_coverage,
                "passed_targets": passed,
                "failures": reasons
            }, rf, indent=2)
            
        return passed, total_coverage, branch_coverage
    except Exception as e:
        print(f"[ERROR] Failed to parse coverage report: {e}")
        return False, 0.0, 0.0

if __name__ == "__main__":
    run_coverage()
