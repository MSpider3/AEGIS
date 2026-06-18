import os
import json

BASELINE_PATH = os.path.join("testing", "baseline_metrics.json")

# Default baseline metrics to initialize if not present
DEFAULT_BASELINE = {
    "protect_time_hybrid_seconds": 25.0,
    "protect_time_face_seconds": 20.0,
    "protect_time_art_seconds": 10.0,
    "watermark_extraction_accuracy_clean": 1.0,
    "watermark_extraction_accuracy_jpg_q50": 0.0, # Known limitation under lossy compression
    "watermark_extraction_accuracy_resize_05": 0.0, # Known limitation if resizing shifts coordinates
    "id_guard_detection_rate": 0.80, # Expected detection target
    "face_cloaking_success_rate": 0.90,
    "poisoning_perturbation_survival_rate": 0.50 # Expected retention rate after bilinear resizing to 224x224
}

def load_baseline():
    if not os.path.exists(BASELINE_PATH):
        print(f"[INFO] Baseline metrics file not found. Creating default at {BASELINE_PATH}...")
        save_metrics(DEFAULT_BASELINE)
        return DEFAULT_BASELINE
    try:
        with open(BASELINE_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load baseline metrics: {e}. Using defaults.")
        return DEFAULT_BASELINE

def save_metrics(metrics):
    try:
        with open(BASELINE_PATH, "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"[INFO] Baseline metrics saved to {BASELINE_PATH}")
    except Exception as e:
        print(f"[ERROR] Failed to save baseline metrics: {e}")

def check_regression(current_metrics):
    baseline = load_baseline()
    regressions = []
    
    # 1. Check processing times (allow up to 30% increase for system fluctuations)
    time_keys = ["protect_time_hybrid_seconds", "protect_time_face_seconds", "protect_time_art_seconds"]
    for key in time_keys:
        if key in current_metrics:
            curr_val = current_metrics[key]
            base_val = baseline.get(key, DEFAULT_BASELINE[key])
            if curr_val > base_val * 1.3:
                regressions.append(f"Performance Regression: {key} increased from {base_val:.2f}s to {curr_val:.2f}s (exceeded 30% threshold)")
                
    # 2. Check accuracy metrics (allow up to 5% decrease or check absolute bounds)
    accuracy_keys = [
        "watermark_extraction_accuracy_clean",
        "watermark_extraction_accuracy_jpg_q50",
        "id_guard_detection_rate",
        "face_cloaking_success_rate",
        "poisoning_perturbation_survival_rate"
    ]
    for key in accuracy_keys:
        if key in current_metrics:
            curr_val = current_metrics[key]
            base_val = baseline.get(key, DEFAULT_BASELINE[key])
            if curr_val < base_val - 0.05:
                regressions.append(f"Accuracy Regression: {key} dropped from {base_val*100:.1f}% to {curr_val*100:.1f}%")

    if regressions:
        print("\n[!] REGRESSION DETECTION FAILED [!]")
        for reg in regressions:
            print(f"  - {reg}")
        return False, regressions
    else:
        print("\n[SUCCESS] No regressions detected against baseline metrics.")
        return True, []

if __name__ == "__main__":
    # Test regression check
    load_baseline()
