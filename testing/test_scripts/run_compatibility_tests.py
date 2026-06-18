import os
import subprocess
import json

BASE_TEMP = "testing"

def test_compatibility():
    print("[INFO] Checking Python cross-version compatibility (3.10, 3.11, 3.12)...")
    
    python_versions = ["python3.10", "python3.11", "python3.12"]
    results = {}
    
    # We want to check if they can import our packages
    # We add the venv site-packages to PYTHONPATH to see if they can use the pre-built aegis_kernel
    site_packages = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "venv", "lib64", "python3.11", "site-packages"))
    if not os.path.exists(site_packages):
        site_packages = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "venv", "lib", "python3.11", "site-packages"))
        
    env = os.environ.copy()
    env["PYTHONPATH"] = f"src:{site_packages}"
    
    for py in python_versions:
        # Check if python version is available on path
        try:
            check_ver = subprocess.run([py, "--version"], capture_output=True, text=True)
            if check_ver.returncode != 0:
                results[py] = {"available": False, "status": "Not available on host"}
                continue
        except Exception:
            results[py] = {"available": False, "status": "Not available on host"}
            continue
            
        # Try to import aegis_kernel and torch
        test_code = """
import sys
print(f"Running Python {sys.version_info.major}.{sys.version_info.minor}")
try:
    import torch
    print("torch: OK")
except Exception as e:
    print(f"torch: FAILED ({e})")

try:
    import aegis_kernel
    print("aegis_kernel: OK")
except Exception as e:
    print(f"aegis_kernel: FAILED ({e})")
"""
        res = subprocess.run([py, "-c", test_code], capture_output=True, text=True, env=env)
        
        results[py] = {
            "available": True,
            "stdout": res.stdout.strip().split("\n"),
            "stderr": res.stderr.strip(),
            "compatible": "aegis_kernel: OK" in res.stdout
        }
        
    print("\n--- Python Version Compatibility Results ---")
    for py, data in results.items():
        if not data["available"]:
            print(f"  {py}: NOT INSTALLED ON HOST")
        else:
            status = "COMPATIBLE" if data["compatible"] else "INCOMPATIBLE"
            print(f"  {py}: {status}")
            print(f"    Details: {data['stdout']}")
            if data["stderr"]:
                print(f"    Error: {data['stderr']}")

    log_path = os.path.join(BASE_TEMP, "logs", "compatibility_report.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"[INFO] Compatibility report saved to {log_path}")
    return results

if __name__ == "__main__":
    test_compatibility()
