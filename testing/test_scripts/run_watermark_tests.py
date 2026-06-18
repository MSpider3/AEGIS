import os
import json
import pytest
from PIL import Image
import aegis_kernel
from cli import parse_seed

BASE_TEMP = "testing"

def test_watermark_robustness():
    """Embed watermark and measure extraction survival across physical/compression transformations."""
    # Create cover image
    cover_path = os.path.join(BASE_TEMP, "generated_images", "watermark_cover_256.png")
    img = Image.new("RGB", (256, 256), color=(128, 128, 128))
    # Add some high-frequency content to help watermarking
    for x in range(0, 256, 16):
        for y in range(0, 256, 16):
            img.putpixel((x, y), (255, 255, 255))
    img.save(cover_path)

    # 1. Embed watermark
    width, height = img.size
    ycbcr = img.convert("YCbCr")
    y_chan, cb_chan, cr_chan = ycbcr.split()
    y_bytes = list(y_chan.tobytes())
    
    payload = "AEGIS-QA-TEST"
    seed = parse_seed("1337")
    
    try:
        y_bytes_watermarked = aegis_kernel.embed_watermark_py(
            y_bytes, width, height, payload, seed, 40.0
        )
    except Exception as e:
        pytest.fail(f"Watermark embedding failed: {e}")
        
    new_y_chan = Image.frombytes("L", (width, height), bytes(y_bytes_watermarked))
    watermarked_img = Image.merge("YCbCr", (new_y_chan, cb_chan, cr_chan)).convert("RGB")
    
    watermarked_path = os.path.join(BASE_TEMP, "transformed_images", "watermarked_base.png")
    watermarked_img.save(watermarked_path, "PNG")
    
    # 2. Test transformations and measure survival
    transformations = {
        "jpeg_q95": lambda im: im.save(os.path.join(BASE_TEMP, "transformed_images", "wm_q95.jpg"), "JPEG", quality=95) or Image.open(os.path.join(BASE_TEMP, "transformed_images", "wm_q95.jpg")),
        "jpeg_q75": lambda im: im.save(os.path.join(BASE_TEMP, "transformed_images", "wm_q75.jpg"), "JPEG", quality=75) or Image.open(os.path.join(BASE_TEMP, "transformed_images", "wm_q75.jpg")),
        "jpeg_q50": lambda im: im.save(os.path.join(BASE_TEMP, "transformed_images", "wm_q50.jpg"), "JPEG", quality=50) or Image.open(os.path.join(BASE_TEMP, "transformed_images", "wm_q50.jpg")),
        "jpeg_q10": lambda im: im.save(os.path.join(BASE_TEMP, "transformed_images", "wm_q10.jpg"), "JPEG", quality=10) or Image.open(os.path.join(BASE_TEMP, "transformed_images", "wm_q10.jpg")),
        "webp_lossy": lambda im: im.save(os.path.join(BASE_TEMP, "transformed_images", "wm_lossy.webp"), "WEBP", quality=80) or Image.open(os.path.join(BASE_TEMP, "transformed_images", "wm_lossy.webp")),
        "resize_09": lambda im: im.resize((int(width*0.9), int(height*0.9)), Image.Resampling.BILINEAR),
        "resize_05": lambda im: im.resize((int(width*0.5), int(height*0.5)), Image.Resampling.BILINEAR),
        "crop_98": lambda im: im.crop((int(width*0.01), int(height*0.01), int(width*0.99), int(height*0.99))),
        "crop_90": lambda im: im.crop((int(width*0.05), int(height*0.05), int(width*0.95), int(height*0.95))),
        "crop_50": lambda im: im.crop((int(width*0.25), int(height*0.25), int(width*0.75), int(height*0.75))),
        "rotate_90": lambda im: im.rotate(90, expand=True),
        "brightness_high": lambda im: Image.new("RGB", im.size) # dummy placeholder, will apply actual enhancement
    }
    
    results = {}
    
    # Check baseline (clean)
    results["clean"] = verify_image(watermarked_img, payload, seed)
    
    for name, tf in transformations.items():
        try:
            if name == "brightness_high":
                from PIL import ImageEnhance
                tf_img = ImageEnhance.Brightness(watermarked_img).enhance(1.3)
            else:
                tf_img = tf(watermarked_img)
            
            results[name] = verify_image(tf_img, payload, seed)
        except Exception as e:
            results[name] = {"success": False, "reason": str(e), "ber": 1.0}
            
    print("\n--- Watermark Robustness Results ---")
    for name, res in results.items():
        status = "PASSED" if res["success"] else "FAILED"
        print(f"  {name}: {status} (BER: {res['ber']:.2f}, Reason: {res.get('reason', 'N/A')})")
        
    # Save report
    log_path = os.path.join(BASE_TEMP, "logs", "watermark_report.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"[INFO] Watermark report saved to {log_path}")
    assert results["clean"]["success"]

def verify_image(img_obj, expected_payload, seed):
    try:
        w, h = img_obj.size
        ycbcr = img_obj.convert("YCbCr")
        y_chan, _, _ = ycbcr.split()
        y_bytes = list(y_chan.tobytes())
        
        extracted = aegis_kernel.detect_watermark_py(y_bytes, w, h, seed)
        if extracted == expected_payload:
            return {"success": True, "ber": 0.0, "payload": extracted}
        else:
            # Check length or character diffs to get a rough character error rate (as proxy for BER)
            diffs = sum(1 for c1, c2 in zip(extracted, expected_payload) if c1 != c2)
            diffs += abs(len(extracted) - len(expected_payload))
            cer = diffs / max(len(expected_payload), 1)
            return {"success": False, "ber": cer, "payload": extracted, "reason": "Payload mismatch"}
    except Exception as e:
        return {"success": False, "ber": 1.0, "reason": str(e)}

if __name__ == "__main__":
    test_watermark_robustness()
