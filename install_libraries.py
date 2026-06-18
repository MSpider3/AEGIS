import sys
import subprocess
import shutil
import platform

def run_command(cmd_list):
    """Helper to run subprocess commands with live streaming output."""
    print(f"\n[RUNNING] {' '.join(cmd_list)}")
    try:
        subprocess.run(cmd_list, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Command failed with exit code {e.returncode}")
        sys.exit(1)

def detect_hardware():
    """Detects system OS, CPU architecture, and NVIDIA GPU availability."""
    system_os = platform.system().lower()
    machine_arch = platform.machine().lower()
    
    print("=== AEGIS System Hardware Detection ===")
    print(f"Detected Operating System: {platform.system()} ({platform.release()})")
    print(f"Detected Architecture: {platform.machine()}")
    
    # Check for NVIDIA GPU
    has_nvidia = False
    if shutil.which("nvidia-smi") is not None:
        try:
            # Check if we can successfully query nvidia-smi
            result = subprocess.run(["nvidia-smi"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode == 0:
                has_nvidia = True
        except Exception:
            pass
            
    # Check for Apple Silicon
    is_apple_silicon = (system_os == "darwin" and "arm" in machine_arch)
    
    if has_nvidia:
        print("Hardware Target: NVIDIA GPU (CUDA accelerated)")
        return "nvidia"
    elif is_apple_silicon:
        print("Hardware Target: Apple Silicon (Metal/MPS accelerated)")
        return "apple_silicon"
    else:
        print("Hardware Target: Standard CPU / Integrated Graphics")
        return "cpu"

def main():
    target = detect_hardware()
    
    # Determine the install arguments for the torch stack
    torch_packages = ["torch>=2.0.0", "torchvision>=0.15.0", "torchaudio"]
    
    if target == "nvidia":
        # Install CUDA-enabled PyTorch
        # Standard stable CUDA build for Linux/Windows is currently cu121/cu124
        print("Preparing installation of CUDA-enabled PyTorch (cu121)...")
        install_cmd = [sys.executable, "-m", "pip", "install"] + torch_packages + ["--index-url", "https://download.pytorch.org/whl/cu121"]
    elif target == "apple_silicon":
        print("Preparing installation of standard Mac (MPS) PyTorch...")
        install_cmd = [sys.executable, "-m", "pip", "install"] + torch_packages
    else:
        print("Preparing installation of CPU-only PyTorch...")
        install_cmd = [sys.executable, "-m", "pip", "install"] + torch_packages
        
    # 1. Install GPU/CPU Torch Stack
    print("\n--- Step 1: Installing PyTorch Ecosystem ---")
    run_command(install_cmd)
    
    # 2. Install requirements.txt
    print("\n--- Step 2: Installing Core Requirements ---")
    requirements_cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    run_command(requirements_cmd)
    
    print("\n[SUCCESS] All dependencies have been successfully installed!")

if __name__ == "__main__":
    main()
