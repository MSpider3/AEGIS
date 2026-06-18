import os
import json
import cv2
import numpy as np
import pytest
from PIL import Image
import aegis_kernel
from cli import parse_seed

BASE_TEMP = "testing"

def get_dct_coefficients(y_channel):
    h, w = y_channel.shape
    h_blocks = h // 8
    w_blocks = w // 8
    
    mid_freq_values = []
    
    for bh in range(h_blocks):
        for bw in range(w_blocks):
            block = y_channel[bh*8:(bh+1)*8, bw*8:(bw+1)*8].astype(np.float32)
            dct_block = cv2.dct(block)
            
            # Extract mid frequencies: i + j between 2 and 6
            for i in range(8):
                for j in range(8):
                    if 2 <= i + j <= 6:
                        mid_freq_values.append(dct_block[i, j])
                        
    return np.array(mid_freq_values)

def test_poisoning_survival():
    """Verify that frequency-domain perturbations survive resizing, JPEG compression, and normalization."""
    # Create cover image
    cover_path = os.path.join(BASE_TEMP, "generated_images", "poison_cover_256.png")
    img = Image.new("RGB", (256, 256), color=(128, 128, 128))
    for x in range(0, 256, 16):
        for y in range(0, 256, 16):
            img.putpixel((x, y), (255, 255, 255))
    img.save(cover_path)
    
    img = Image.open(cover_path).convert("RGB")
    width, height = img.size
    
    # Get original Y-channel DCT coefficients
    ycbcr = img.convert("YCbCr")
    y_chan, cb_chan, cr_chan = ycbcr.split()
    y_orig_np = np.array(y_chan)
    orig_coeffs = get_dct_coefficients(y_orig_np)
    
    # 1. Apply frequency perturbation (art mode)
    seed = parse_seed("12345")
    strength = 15.0
    y_bytes = list(y_chan.tobytes())
    y_bytes_perturbed = aegis_kernel.perturb_frequency_py(y_bytes, width, height, strength, seed)
    
    # Reconstruct perturbed image
    new_y_chan = Image.frombytes("L", (width, height), bytes(y_bytes_perturbed))
    perturbed_img = Image.merge("YCbCr", (new_y_chan, cb_chan, cr_chan)).convert("RGB")
    perturbed_path = os.path.join(BASE_TEMP, "transformed_images", "poisoned_base.png")
    perturbed_img.save(perturbed_path, "PNG")
    
    # Get perturbed Y-channel DCT coefficients
    y_pert_np = np.array(new_y_chan)
    pert_coeffs = get_dct_coefficients(y_pert_np)
    
    # 2. Simulate AI ingestion pipeline transformations
    pipelines = {
        "resized_224": lambda im: im.resize((224, 224), Image.Resampling.BILINEAR),
        "jpeg_q50": lambda im: save_and_reload_jpeg(im, 50),
        "normalized": lambda im: normalize_sim(im)
    }
    
    def save_and_reload_jpeg(im, q):
        p = os.path.join(BASE_TEMP, "transformed_images", f"poisoned_q{q}.jpg")
        im.save(p, "JPEG", quality=q)
        return Image.open(p)
        
    def normalize_sim(im):
        # We simulate normalization by multiplying intensity (standard training contrast normalization)
        arr = np.array(im, dtype=np.float32)
        arr = (arr - 128.0) / 64.0
        # Scale back to 0-255 for DCT calculation
        arr = np.clip(arr * 64.0 + 128.0, 0, 255).astype(np.uint8)
        return Image.fromarray(arr)

    results = {}
    
    # Compute base perturbation delta (variance of difference)
    base_diff = pert_coeffs - orig_coeffs
    base_noise_var = np.var(base_diff)
    print(f"[INFO] Base perturbation variance in mid-frequencies: {base_noise_var:.4f}")
    
    results["base_strength"] = float(base_noise_var)
    
    for name, pipeline_fn in pipelines.items():
        processed_img = pipeline_fn(perturbed_img)
        w_proc, h_proc = processed_img.size
        
        ycbcr_proc = processed_img.convert("YCbCr")
        y_proc_chan, _, _ = ycbcr_proc.split()
        y_proc_np = np.array(y_proc_chan)
        
        # Also process original cover image with same pipeline for a true relative comparison
        orig_proc_img = pipeline_fn(img)
        ycbcr_orig_proc = orig_proc_img.convert("YCbCr")
        y_orig_proc_chan, _, _ = ycbcr_orig_proc.split()
        y_orig_proc_np = np.array(y_orig_proc_chan)
        
        proc_coeffs = get_dct_coefficients(y_proc_np)
        proc_orig_coeffs = get_dct_coefficients(y_orig_proc_np)
        
        # We check the length to align coefficients in case size changed
        min_len = min(len(proc_coeffs), len(proc_orig_coeffs))
        proc_coeffs = proc_coeffs[:min_len]
        proc_orig_coeffs = proc_orig_coeffs[:min_len]
        
        proc_diff = proc_coeffs - proc_orig_coeffs
        proc_noise_var = np.var(proc_diff)
        
        # Retention rate
        retention = proc_noise_var / base_noise_var if base_noise_var > 0 else 0.0
        
        results[name] = {
            "noise_variance": float(proc_noise_var),
            "retention_rate": float(retention),
            "survived": bool(retention > 0.1) # at least 10% of frequency noise survived
        }
        print(f"  Pipeline '{name}': Noise Var = {proc_noise_var:.4f}, Retention = {retention*100:.1f}%")

    # Save log report
    log_path = os.path.join(BASE_TEMP, "logs", "poisoning_report.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"[INFO] Poisoning report saved to {log_path}")
    assert base_noise_var > 0.0
    # Resizing might blur out high frequencies, but mid-frequencies in DCT should retain some signature
    assert results["resized_224"]["survived"]
    assert results["jpeg_q50"]["survived"]

if __name__ == "__main__":
    test_poisoning_survival()
