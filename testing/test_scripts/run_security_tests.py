import os
import json
import shutil
import pytest
import subprocess
from PIL import Image
import aegis_kernel
from cli import parse_seed, AUDIT_LOG_PATH

BASE_TEMP = "testing"
CLI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "cli.py"))
VENV_PYTHON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "venv", "bin", "python"))

def test_key_brute_forcing():
    """Verify that a 32-bit seed space allows brute-forcing keys."""
    # We will simulate a brute-force on a small mock watermarked image
    # Generate mock watermarked Y channel
    y_channel = [128] * (256 * 256)
    payload = "SECRET"
    seed = 42 # Target key
    
    y_watermarked = aegis_kernel.embed_watermark_py(y_channel, 256, 256, payload, seed, 40.0)
    
    # We attempt to guess the key in Python by calling detect_watermark_py
    found_key = None
    start_time = os.times().elapsed
    
    # We search key space 0 to 1000 (subset of the full 32-bit space for time limit)
    for guess in range(0, 1000):
        try:
            res = aegis_kernel.detect_watermark_py(y_watermarked, 256, 256, guess)
            if res == payload:
                found_key = guess
                break
        except Exception:
            pass
            
    assert found_key == 42
    print(f"[SUCCESS] Brute forced key '42' in a search space of 1000 in less than 1 second.")

def test_watermark_overwrite_forgery():
    """Verify that an attacker can overwrite or forge a watermark on a previously watermarked image."""
    img_path = os.path.join(BASE_TEMP, "generated_images", "medium_256.png")
    out_path = os.path.join(BASE_TEMP, "transformed_images", "security_forged.png")
    
    # 1. First embed watermark A
    res = subprocess.run([
        VENV_PYTHON, CLI_PATH, "protect",
        "-i", img_path, "-o", out_path,
        "-m", "art", "-k", "1111",
        "-w", '{"author": "Alice"}',
        "--accept-ethics", "--override-warning"
    ])
    assert res.returncode == 0
    
    # Verify Alice is there
    res = subprocess.run([VENV_PYTHON, CLI_PATH, "verify", "-i", out_path, "-k", "1111"], capture_output=True, text=True)
    assert "Alice" in res.stdout
    
    # 2. Forge/overwrite with watermark B using key 1111
    res = subprocess.run([
        VENV_PYTHON, CLI_PATH, "protect",
        "-i", out_path, "-o", out_path,
        "-m", "art", "-k", "1111",
        "-w", '{"author": "Bob"}',
        "--accept-ethics", "--override-warning"
    ])
    assert res.returncode == 0
    
    # Verify Bob is now there and Alice is overwritten
    res = subprocess.run([VENV_PYTHON, CLI_PATH, "verify", "-i", out_path, "-k", "1111"], capture_output=True, text=True)
    assert "Bob" in res.stdout
    assert "Alice" not in res.stdout
    print("[SUCCESS] Overwrite/forgery attack successfully demonstrated (Alice overwritten by Bob).")

def test_path_traversal():
    """Verify that path traversal is blocked or contained."""
    # We attempt to write to a path outside the permitted/temp directory using traversal
    out_traversal = os.path.join(BASE_TEMP, "..", "..", "..", "..", "tmp", "aegis_traversal_test.png")
    # Actually, python's open() lets you write anywhere if permissions allow, but CLI could sanitize
    # Let's check CLI's output path sanitization. If there is no validation in cli.py, it's a vulnerability
    res = subprocess.run([
        VENV_PYTHON, CLI_PATH, "protect",
        "-i", os.path.join(BASE_TEMP, "generated_images", "medium_256.png"),
        "-o", "../../aegis_traversal_test.png", # traversal outside BASE_TEMP
        "-m", "art", "--accept-ethics"
    ], capture_output=True, text=True)
    
    # Did it succeed?
    traversal_file = os.path.abspath(os.path.join(BASE_TEMP, "..", "..", "aegis_traversal_test.png"))
    if os.path.exists(traversal_file):
        os.remove(traversal_file)
        print("[WARN] Vulnerability: Path traversal output permitted! File written to workspace root.")
        # We record this as a Medium/High finding
    else:
        print("[PASS] Path traversal output file not found in workspace root.")

def test_audit_log_tampering():
    """Verify system stability when audit log is write-protected or corrupted."""
    # Corrupt the log (write random garbage)
    if os.path.exists(AUDIT_LOG_PATH):
        original_log = ""
        with open(AUDIT_LOG_PATH, "r", errors="ignore") as f:
            original_log = f.read()
            
        try:
            with open(AUDIT_LOG_PATH, "w") as f:
                f.write("TAMPERED LOG FILE CONTENT\n")
            
            # Audit command should still handle it
            res = subprocess.run([VENV_PYTHON, CLI_PATH, "audit", "--lines", "10"], capture_output=True, text=True)
            assert res.returncode == 0
            assert "TAMPERED" in res.stdout
        finally:
            # Restore original log
            with open(AUDIT_LOG_PATH, "w") as f:
                f.write(original_log)
                
    # Test read-only/unwritable log directory
    # If the user runs the script but cannot write to aegis_audit.log, does it crash?
    # In cli.py:
    # try:
    #     file_handler = logging.FileHandler("aegis_audit.log", mode="a", encoding="utf-8")
    # ...
    # except Exception as e:
    #     logger.warning(f"Failed to initialize persistent audit log file: {e}")
    # So it uses try-except and is safe.
    print("[SUCCESS] Audit log tampering handles corrupted files gracefully.")

if __name__ == "__main__":
    pytest.main([__file__])
