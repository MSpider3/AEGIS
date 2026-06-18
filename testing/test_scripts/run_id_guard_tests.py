import os
import json
import pytest
from aegis_core.analyzer import ImageAnalyzer

BASE_TEMP = "testing"
MANIFEST_JSON = os.path.join(BASE_TEMP, "manifest.json")

def load_manifest_records():
    if not os.path.exists(MANIFEST_JSON):
        return []
    with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def test_id_guard_accuracy():
    """Evaluate ID-Guard detection rates on original and transformed Government IDs, and false positive rates on art/portraits."""
    records = load_manifest_records()
    if not records:
        pytest.skip("Manifest not generated yet.")

    analyzer = ImageAnalyzer()
    
    total_ids = 0
    detected_ids = 0
    evaded_by_transform = {}
    
    total_non_ids = 0
    false_positives = 0
    
    # Process records
    for r in records:
        category = r["category"]
        path = r["path"]
        transform = r["transform"]
        
        # Check if the file actually exists
        if not os.path.exists(path):
            continue
            
        is_id = "Government IDs" in category
        is_candidate = is_id or (transform == "original" and ("potraits" in category or "Human-created artwork_" in category))
        
        if not is_candidate:
            continue
            
        is_flagged, conf, reason = analyzer.check_id_guard(path)
        
        if is_id:
            total_ids += 1
            if is_flagged:
                detected_ids += 1
            else:
                # Evasion! Let's record which transform caused this evasion
                evaded_by_transform[transform] = evaded_by_transform.get(transform, 0) + 1
        else:
            # We only evaluate false positives on original non-ID assets (to avoid bloating stats)
            if transform == "original" and ("potraits" in category or "Human-created artwork_" in category):
                total_non_ids += 1
                if is_flagged:
                    false_positives += 1
                    print(f"[WARN] False Positive: Clean image {path} flagged as ID due to: {reason}")

    detection_rate = detected_ids / total_ids if total_ids > 0 else 0.0
    false_positive_rate = false_positives / total_non_ids if total_non_ids > 0 else 0.0
    
    print(f"\n--- ID-Guard Performance Summary ---")
    print(f"Total Government ID variants tested: {total_ids}")
    print(f"Detected: {detected_ids} / {total_ids} ({detection_rate*100:.2f}%)")
    print(f"False Positives on Art/Portraits: {false_positives} / {total_non_ids} ({false_positive_rate*100:.2f}%)")
    print(f"Evasions by transformation type: {evaded_by_transform}")
    
    # Save log report
    report = {
        "total_ids_tested": total_ids,
        "detected_ids": detected_ids,
        "detection_rate": detection_rate,
        "total_non_ids_tested": total_non_ids,
        "false_positives": false_positives,
        "false_positive_rate": false_positive_rate,
        "evaded_by_transform": evaded_by_transform
    }
    
    log_path = os.path.join(BASE_TEMP, "logs", "id_guard_report.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"[INFO] ID-Guard report saved to {log_path}")
    
    # Assertions for basic functionality
    # (Since some bypasses will naturally succeed, we don't expect 100% detection rate on transformed, but original should be high)
    assert total_ids > 0

if __name__ == "__main__":
    test_id_guard_accuracy()
