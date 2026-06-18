import os
import time
import resource
import json
from PIL import Image
import torch
import aegis_kernel
from aegis_core.cloaking import PgdCloaker
from cli import parse_seed

BASE_TEMP = "testing"

def get_memory_usage_mb():
    # resource.getrusage returns bytes on macOS, but kilobytes on Linux.
    # Since the OS is Linux, it returns kilobytes.
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return usage / 1024.0

def benchmark_run():
    print("[INFO] Starting AEGIS Performance Benchmarks...")
    
    results = {}
    
    # Pre-load/create benchmark test images
    img_sizes = {
        "small": (256, 256),
        "medium": (1024, 1024),
        # We use 2048 instead of 3000 to keep the memory footprint reasonable during local test runs
        "large": (2048, 2048)
    }
    
    # Ensure they exist or create them
    for name, size in img_sizes.items():
        p = os.path.join(BASE_TEMP, "benchmark_data", f"bench_{name}.png")
        if not os.path.exists(p):
            im = Image.new("RGB", size, color=(128, 128, 128))
            im.save(p)
            
    # Initialize PGD Cloaker
    print("[INFO] Warm-up PyTorch model...")
    try:
        cloaker = PgdCloaker(surrogate_name="mobilenet_v2", offline=True)
    except Exception:
        cloaker = PgdCloaker(surrogate_name="mobilenet_v2", offline=False)
        
    seed = parse_seed("1337")
    
    for size_name, size in img_sizes.items():
        print(f"\n--- Benchmarking Size: {size_name} ({size[0]}x{size[1]}) ---")
        img_path = os.path.join(BASE_TEMP, "benchmark_data", f"bench_{size_name}.png")
        
        # 1. Benchmark PyTorch PGD Cloaking (Python-only / GPU/CPU)
        # We run 5 iterations/steps for benchmarking
        start_mem = get_memory_usage_mb()
        start_time = time.perf_counter()
        
        # Run PGD cloaking
        _ = cloaker.cloak_image(img_path, eps=8.0, steps=5)
        
        end_time = time.perf_counter()
        end_mem = get_memory_usage_mb()
        
        pgd_duration = end_time - start_time
        pgd_mem_growth = end_mem - start_mem
        
        print(f"  PGD Cloaking: Time = {pgd_duration:.4f}s, Mem Growth = {pgd_mem_growth:.2f} MB")
        
        # 2. Benchmark Rust Frequency Perturbation
        img = Image.open(img_path).convert("RGB")
        width, height = img.size
        ycbcr = img.convert("YCbCr")
        y_chan, cb_chan, cr_chan = ycbcr.split()
        
        # We benchmark the list conversion + Rust execution + list reconstruction
        start_mem = get_memory_usage_mb()
        start_time = time.perf_counter()
        
        y_bytes = list(y_chan.tobytes())
        y_bytes_perturbed = aegis_kernel.perturb_frequency_py(y_bytes, width, height, 5.0, seed)
        _ = Image.frombytes("L", (width, height), bytes(y_bytes_perturbed))
        
        end_time = time.perf_counter()
        end_mem = get_memory_usage_mb()
        
        rust_duration = end_time - start_time
        rust_mem_growth = end_mem - start_mem
        
        print(f"  Rust Freq Perturb (with PyO3 overhead): Time = {rust_duration:.4f}s, Mem Growth = {rust_mem_growth:.2f} MB")
        
        # 3. Benchmark Rust-only execution vs Python List conversion overhead
        # Let's isolate the list conversion overhead
        start_time = time.perf_counter()
        y_bytes_dummy = list(y_chan.tobytes())
        _ = bytes(y_bytes_dummy)
        end_time = time.perf_counter()
        conversion_overhead = end_time - start_time
        
        print(f"  Python-Rust conversion overhead: {conversion_overhead:.4f}s ({conversion_overhead/rust_duration*100:.1f}% of Rust stage)")
        
        results[size_name] = {
            "resolution": f"{size[0]}x{size[1]}",
            "pgd_duration_seconds": pgd_duration,
            "pgd_memory_growth_mb": pgd_mem_growth,
            "rust_duration_seconds": rust_duration,
            "rust_memory_growth_mb": rust_mem_growth,
            "conversion_overhead_seconds": conversion_overhead,
            "pure_rust_duration_est_seconds": max(rust_duration - conversion_overhead, 0.0001)
        }

    # Save benchmark log
    log_path = os.path.join(BASE_TEMP, "logs", "benchmark_report.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"\n[SUCCESS] Benchmarking completed. Written to {log_path}")

if __name__ == "__main__":
    benchmark_run()
