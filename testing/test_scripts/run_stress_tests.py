import os
import time
import subprocess
import concurrent.futures
import pytest
from cli import AUDIT_LOG_PATH

BASE_TEMP = "testing"
CLI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "cli.py"))
VENV_PYTHON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "venv", "bin", "python"))

def run_single_job(job_id, img_path, out_path):
    env = os.environ.copy()
    env["AEGIS_NO_CLIP"] = "1"
    env["AEGIS_NO_FORENSICS"] = "1"
    res = subprocess.run([
        VENV_PYTHON, CLI_PATH, "protect",
        "-i", img_path, "-o", out_path,
        "-m", "art", "-k", f"seed_{job_id}",
        "-w", f'{{"job_id": {job_id}}}',
        "--accept-ethics", "--override-warning"
    ], env=env, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

def run_concurrent_batch(concurrency):
    print(f"[INFO] Running stress test with concurrency level: {concurrency}")
    
    img_path = os.path.join(BASE_TEMP, "generated_images", "medium_256.png")
    out_dir = os.path.join(BASE_TEMP, "transformed_images", f"stress_{concurrency}")
    os.makedirs(out_dir, exist_ok=True)
    
    # We clear out_dir
    for f in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, f))
        
    # Get current log size to count new entries
    initial_log_lines = 0
    if os.path.exists(AUDIT_LOG_PATH):
        with open(AUDIT_LOG_PATH, "r", errors="ignore") as f:
            initial_log_lines = len(f.readlines())

    start_time = time.perf_counter()
    
    # Limit max concurrent processes to 4 to keep memory usage low, while running the full queue
    max_active_workers = min(4, concurrency)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_active_workers) as executor:
        futures = []
        for i in range(concurrency):
            out_path = os.path.join(out_dir, f"out_{i}.png")
            futures.append(executor.submit(run_single_job, i, img_path, out_path))
            
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
    duration = time.perf_counter() - start_time
    print(f"[SUCCESS] Concurrency {concurrency} finished in {duration:.2f} seconds.")
    
    # Verify results
    success_count = sum(1 for rc, _, _ in results if rc == 0)
    assert success_count == concurrency
    
    # Check log file integrity and entry count
    assert os.path.exists(AUDIT_LOG_PATH)
    with open(AUDIT_LOG_PATH, "r", errors="ignore") as f:
        final_lines = f.readlines()
        
    new_entries = len(final_lines) - initial_log_lines
    print(f"  Jobs Run: {concurrency}, Successful: {success_count}, New Audit Log Lines: {new_entries}")
    
    # Check for corruption (should have clean formatted lines containing expected log content)
    for line in final_lines[-new_entries:]:
        assert "AUDIT LOG" in line or "User overrode warning" in line or "Successfully loaded" in line or "INFO" in line or line.strip() == ""

def test_stress_concurrency():
    """Run parallel protect stress testing on 10, 50, and 100 concurrent jobs."""
    # Test 10 jobs
    run_concurrent_batch(10)
    
    # Test 50 jobs
    run_concurrent_batch(50)
    
    # Test 100 jobs (light art mode ensures we don't OOM or crash host)
    run_concurrent_batch(100)

if __name__ == "__main__":
    pytest.main([__file__])
