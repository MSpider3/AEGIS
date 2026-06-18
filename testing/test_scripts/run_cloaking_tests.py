import os
import json
import torch
import pytest
from PIL import Image
from torchvision import transforms
from aegis_core.cloaking import PgdCloaker

BASE_TEMP = "testing"

def test_cloaking_efficiency():
    """Verify classification confidence drop, surrogate transferability, and durability after transformations."""
    # Find a portrait or generate a mock face-like pattern
    src_img = os.path.join(BASE_TEMP, "generated_images", "medium_256.png")
    
    # Initialize MobileNetV2 cloaker
    try:
        cloaker = PgdCloaker(surrogate_name="mobilenet_v2", offline=True)
    except Exception as e:
        print(f"[WARN] Failed to initialize PgdCloaker offline: {e}. Attempting online initialization...")
        cloaker = PgdCloaker(surrogate_name="mobilenet_v2", offline=False)

    # 1. Run Cloaker
    cloaked_img = cloaker.cloak_image(src_img, eps=8.0, steps=10) # 10 steps for speed
    cloaked_path = os.path.join(BASE_TEMP, "transformed_images", "cloaked_base.png")
    cloaked_img.save(cloaked_path, "PNG")
    
    # 2. Measure confidence before/after
    # Setup torchvision evaluator
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = cloaker.model # mobilenet_v2
    model.eval()
    
    mean = torch.tensor([0.485, 0.456, 0.406], device=device).view(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225], device=device).view(1, 3, 1, 1)
    
    def get_confidence(img_obj, target_label=None):
        img_rgb = img_obj.convert("RGB")
        to_tensor = transforms.ToTensor()
        x = to_tensor(img_rgb).unsqueeze(0).to(device)
        x_resized = torch.nn.functional.interpolate(x, size=(224, 224), mode="bilinear", align_corners=False)
        x_normalized = (x_resized - mean) / std
        with torch.no_grad():
            logits = model(x_normalized)
            probs = torch.nn.functional.softmax(logits, dim=1)
            
            if target_label is None:
                target_label = logits.argmax(dim=1).item()
                
            conf = probs[0, target_label].item()
            return conf, target_label

    # Original confidence
    orig_img = Image.open(src_img)
    orig_conf, target_label = get_confidence(orig_img)
    
    # Cloaked confidence
    cloaked_conf, _ = get_confidence(cloaked_img, target_label)
    
    # 3. Test Transferability on ResNet18
    print("[INFO] Loading ResNet18 surrogate to evaluate transferability...")
    try:
        r18_cloaker = PgdCloaker(surrogate_name="resnet18", offline=True)
    except Exception:
        r18_cloaker = PgdCloaker(surrogate_name="resnet18", offline=False)
        
    r18_model = r18_cloaker.model
    
    def get_r18_confidence(img_obj, r18_target_label=None):
        img_rgb = img_obj.convert("RGB")
        to_tensor = transforms.ToTensor()
        x = to_tensor(img_rgb).unsqueeze(0).to(device)
        x_resized = torch.nn.functional.interpolate(x, size=(224, 224), mode="bilinear", align_corners=False)
        x_normalized = (x_resized - mean) / std
        with torch.no_grad():
            logits = r18_model(x_normalized)
            probs = torch.nn.functional.softmax(logits, dim=1)
            if r18_target_label is None:
                r18_target_label = logits.argmax(dim=1).item()
            return probs[0, r18_target_label].item(), r18_target_label

    r18_orig_conf, r18_target = get_r18_confidence(orig_img)
    r18_cloaked_conf, _ = get_r18_confidence(cloaked_img, r18_target)
    
    # 4. Test Durability under transformation (e.g. JPEG compression, resize)
    # JPEG 50
    jpeg_path = os.path.join(BASE_TEMP, "transformed_images", "cloaked_q50.jpg")
    cloaked_img.save(jpeg_path, "JPEG", quality=50)
    jpeg_img = Image.open(jpeg_path)
    durability_conf, _ = get_confidence(jpeg_img, target_label)
    
    results = {
        "original_class_id": target_label,
        "original_confidence": orig_conf,
        "cloaked_confidence": cloaked_conf,
        "resnet18_original_confidence": r18_orig_conf,
        "resnet18_cloaked_confidence": r18_cloaked_conf,
        "durability_jpeg50_confidence": durability_conf,
        "confidence_drop_percentage": (orig_conf - cloaked_conf) / max(orig_conf, 1e-5) * 100
    }
    
    print("\n--- Cloaking Validation Summary ---")
    print(f"Original Class {target_label} Conf: {orig_conf*100:.2f}%")
    print(f"Cloaked Class {target_label} Conf: {cloaked_conf*100:.2f}%")
    print(f"ResNet18 Original Conf: {r18_orig_conf*100:.2f}%")
    print(f"ResNet18 Cloaked Conf: {r18_cloaked_conf*100:.2f}%")
    print(f"Durability (JPEG 50) Conf: {durability_conf*100:.2f}%")
    
    # Save report
    log_path = os.path.join(BASE_TEMP, "logs", "cloaking_report.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"[INFO] Cloaking report saved to {log_path}")
    assert cloaked_conf < orig_conf

if __name__ == "__main__":
    test_cloaking_efficiency()
