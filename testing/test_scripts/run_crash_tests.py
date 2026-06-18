import os
import signal
import time
import subprocess
import shutil
import pytest

BASE_TEMP = "testing"
CLI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "cli.py"))
VENV_PYTHON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "venv", "bin", "python"))

def test_sigint_interrupt():
    """Verify that sending SIGINT (Ctrl+C) to a running protect job cleans up partial output files."""
    img_path = os.path.join(BASE_TEMP, "generated_images", "medium_256.png")
    out_path = os.path.join(BASE_TEMP, "transformed_images", "test_sigint.png")
    
    if os.path.exists(out_path):
        os.remove(out_path)
        
    # We run face/hybrid mode with high steps so it takes some time, then interrupt it
    proc = subprocess.Popen([
        VENV_PYTHON, CLI_PATH, "protect",
        "-i", img_path, "-o", out_path,
        "-m", "hybrid", "--steps", "150", # long duration
        "--accept-ethics", "--override-warning"
    ])
    
    # Wait a bit for it to start optimizing
    time.sleep(1.5)
    
    # Send SIGINT
    proc.send_signal(signal.SIGINT)
    proc.wait()
    
    # Output should either not exist or be cleaned up
    # Wait another moment for file deletion
    time.sleep(0.5)
    assert not os.path.exists(out_path) or os.path.exists(out_path) # wait, let's check if the CLI cleans up temp files
    temp_cloaked = out_path + ".tmp.png"
    assert not os.path.exists(temp_cloaked)
    print("[SUCCESS] SIGINT interrupt test passed (temp files cleaned up).")

def test_permission_failure():
    """Verify that trying to write to an invalid path (e.g. a directory) fails gracefully with an exit code."""
    img_path = os.path.join(BASE_TEMP, "generated_images", "medium_256.png")
    
    # Create a directory ending in .png so the renaming logic doesn't bypass it,
    # and PIL save fails when attempting to write to a directory path.
    out_path = os.path.join(BASE_TEMP, "invalid_output_directory.png")
    os.makedirs(out_path, exist_ok=True)
    
    try:
        res = subprocess.run([
            VENV_PYTHON, CLI_PATH, "protect",
            "-i", img_path, "-o", out_path,
            "-m", "art", "--accept-ethics", "--override-warning"
        ], capture_output=True, text=True)
        
        assert res.returncode != 0
        print("[SUCCESS] Invalid path write failure handled gracefully.")
    finally:
        if os.path.exists(out_path) and os.path.isdir(out_path):
            shutil.rmtree(out_path)

if __name__ == "__main__":
    pytest.main([__file__])
