import os
import shutil
import random
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw

# Define directories
BASE_TEMP = "testing"
DIRS = [
    "generated_images",
    "transformed_images",
    "corrupted_files",
    "fuzz_inputs",
    "benchmark_data",
    "attack_samples",
    "screenshots",
    "logs",
    "test_scripts"
]

def setup_directories():
    for d in DIRS:
        os.makedirs(os.path.join(BASE_TEMP, d), exist_ok=True)
    print("[INFO] Directories initialized successfully.")

def generate_synthetic_images():
    print("[INFO] Generating synthetic edge-case images...")
    
    # 1. Tiny 1x1 image
    img_1x1 = Image.new("RGB", (1, 1), color=(255, 0, 0))
    img_1x1.save(os.path.join(BASE_TEMP, "generated_images", "tiny_1x1.png"), "PNG")
    img_1x1.save(os.path.join(BASE_TEMP, "generated_images", "tiny_1x1.jpg"), "JPEG")
    
    # 2. Medium 512x512 image (named medium_256.png for compatibility)
    # Use high-contrast shapes to ensure perceptual aHash remains stable under PGD perturbation.
    img_mid = Image.new("RGB", (512, 512), color=(128, 128, 128))
    draw = ImageDraw.Draw(img_mid)
    draw.rectangle([0, 0, 256, 512], fill=(40, 50, 60))
    draw.ellipse([128, 128, 384, 384], fill=(220, 210, 200))
    img_mid.save(os.path.join(BASE_TEMP, "generated_images", "medium_256.png"), "PNG")

    # 3. Large 3000x3000 image
    img_large = Image.new("RGB", (3000, 3000), color=(0, 0, 255))
    img_large.save(os.path.join(BASE_TEMP, "generated_images", "large_3000.png"), "PNG")
    
    # 4. CMYK Image
    img_cmyk = Image.new("CMYK", (256, 256), color=(0, 255, 255, 0))
    img_cmyk.save(os.path.join(BASE_TEMP, "generated_images", "cmyk_256.jpg"), "JPEG")
    
    # 5. Grayscale Image
    img_gray = Image.new("L", (256, 256), color=128)
    img_gray.save(os.path.join(BASE_TEMP, "generated_images", "gray_256.png"), "PNG")
    
    # 6. Transparent PNG
    img_trans = Image.new("RGBA", (256, 256), color=(255, 128, 0, 128))
    img_trans.save(os.path.join(BASE_TEMP, "generated_images", "transparent_256.png"), "PNG")
    
    # 7. Corrupted/Malformed Files
    with open(os.path.join(BASE_TEMP, "corrupted_files", "empty.png"), "wb") as f:
        pass
    with open(os.path.join(BASE_TEMP, "corrupted_files", "truncated_header.png"), "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x01") # Truncated PNG header
    with open(os.path.join(BASE_TEMP, "corrupted_files", "random_bytes.png"), "wb") as f:
        f.write(bytes(random.getrandbits(8) for _ in range(1024)))
    with open(os.path.join(BASE_TEMP, "corrupted_files", "text_disguised.png"), "w") as f:
        f.write("Not an image file at all!")
        
    print("[INFO] Synthetic images generated.")

def apply_transformations(src_path, filename, category):
    try:
        img = Image.open(src_path)
    except Exception as e:
        print(f"[WARN] Failed to open {src_path}: {e}")
        return []

    # Downsample extremely large images to speed up processing
    max_dim = 1500
    if img.width > max_dim or img.height > max_dim:
        print(f"[INFO] Image {filename} is large ({img.width}x{img.height}). Downsampling for tests...")
        ratio = max_dim / max(img.width, img.height)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.Resampling.BILINEAR)

    basename, ext = os.path.splitext(filename)
    transformed_records = []
    
    # We want to save transformed images inside testing/attack_samples/ or testing/transformed_images/
    # Let's write them to testing/attack_samples/<category>/
    out_dir = os.path.join(BASE_TEMP, "attack_samples", category)
    os.makedirs(out_dir, exist_ok=True)
    
    # Check if we should convert to RGB for saving (some formats like CMYK/RGBA might fail for JPEG)
    rgb_img = img.convert("RGB") if img.mode != "RGB" else img
    
    # Helper to save and record
    def save_and_record(image_obj, transform_name, format_name="PNG"):
        dest_filename = f"{basename}_{transform_name}.{format_name.lower()}"
        dest_path = os.path.join(out_dir, dest_filename)
        try:
            image_obj.save(dest_path, format_name)
            transformed_records.append({
                "original": filename,
                "transformed": dest_filename,
                "path": dest_path,
                "transform": transform_name,
                "category": category
            })
        except Exception as e:
            print(f"[WARN] Failed to save {dest_path}: {e}")
            
    # 1. Cropping
    # 50% center crop
    w, h = img.size
    if w > 10 and h > 10:
        crop_50 = img.crop((w // 4, h // 4, 3 * w // 4, 3 * h // 4))
        save_and_record(crop_50, "crop_50")
        
        # 90% center crop (subtle crop)
        crop_90 = img.crop((w // 20, h // 20, 19 * w // 20, 19 * h // 20))
        save_and_record(crop_90, "crop_90")

    # 2. Rotation
    # 90 degrees
    rot_90 = img.rotate(90, expand=True)
    save_and_record(rot_90, "rotate_90")
    # 45 degrees (arbitrary rotation with background filling)
    rot_45 = img.rotate(45, expand=True)
    save_and_record(rot_45, "rotate_45")

    # 3. Resizing
    # 0.5x scaling
    if w > 2 and h > 2:
        resize_05 = img.resize((w // 2, h // 2), Image.Resampling.BILINEAR)
        save_and_record(resize_05, "resize_05")
    # 2.0x scaling
    resize_20 = img.resize((w * 2, h * 2), Image.Resampling.BILINEAR)
    save_and_record(resize_20, "resize_20")

    # 4. JPEG Quality Compression
    qualities = [100, 75, 50, 25, 10, 5]
    for q in qualities:
        save_and_record(rgb_img, f"jpeg_q{q}", "JPEG")

    # 5. Formats
    save_and_record(rgb_img, "to_webp", "WEBP")
    
    # 6. Blur and Denoise
    blur_g = img.filter(ImageFilter.GaussianBlur(radius=3))
    save_and_record(blur_g, "blur_gaussian")
    # Median filter (denoise simulation)
    if img.mode in ["L", "RGB"]:
        denoise_m = img.filter(ImageFilter.MedianFilter(size=3))
        save_and_record(denoise_m, "denoise_median")

    # 7. Brightness & Contrast
    enh_b = ImageEnhance.Brightness(img).enhance(1.3)
    save_and_record(enh_b, "brightness_high")
    enh_b_low = ImageEnhance.Brightness(img).enhance(0.7)
    save_and_record(enh_b_low, "brightness_low")
    
    enh_c = ImageEnhance.Contrast(img).enhance(1.5)
    save_and_record(enh_c, "contrast_high")

    # 8. Sharpening
    sharp = img.filter(ImageFilter.SHARPEN)
    save_and_record(sharp, "sharpen")

    # 9. Noise Injection
    if img.mode == "RGB":
        arr = np.array(img, dtype=np.float32)
        noise = np.random.normal(0, 15, arr.shape)
        noisy_arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        noisy_img = Image.fromarray(noisy_arr)
        save_and_record(noisy_img, "noise_gaussian")

    # 10. Perspective Distortion
    # Apply a simple affine shear
    shear_img = img.transform(img.size, Image.Transform.AFFINE, (1, 0.1, 0, 0.1, 1, 0))
    save_and_record(shear_img, "perspective_shear")

    # 11. Simulated Screenshot
    # We simulate a screenshot by placing the image inside a larger gray canvas with a white browser header
    canvas_w = w + 100
    canvas_h = h + 150
    screenshot_canvas = Image.new("RGB", (canvas_w, canvas_h), color=(128, 128, 128))
    # Draw simple window bar
    draw = ImageDraw.Draw(screenshot_canvas)
    draw.rectangle([50, 25, canvas_w - 50, 75], fill=(200, 200, 200))
    # Paste image inside
    screenshot_canvas.paste(rgb_img, (50, 75))
    save_and_record(screenshot_canvas, "simulated_screenshot")

    return transformed_records

def process_dataset():
    src_dir = os.path.join(BASE_TEMP, "aegis_testing_temp")
    if not os.path.exists(src_dir):
        print(f"[ERROR] Source testing directory '{src_dir}' not found.")
        return []
    
    all_records = []
    
    # Categories to process
    categories = [
        "potraits",
        "ai gen images",
        "Human-created artwork_",
        "Government IDs",
        "Screnshots",
        "Watermarked images",
        "edge cases"
    ]
    
    for cat in categories:
        cat_path = os.path.join(src_dir, cat)
        if not os.path.exists(cat_path):
            print(f"[WARN] Category path '{cat_path}' does not exist.")
            continue
            
        print(f"[INFO] Processing category '{cat}'...")
        # Walk recursively to find all files
        for root, _, files in os.walk(cat_path):
            # Calculate category relative subdirectory if any
            rel_dir = os.path.relpath(root, cat_path)
            category_label = cat if rel_dir == "." else f"{cat}/{rel_dir}"
            
            for file in files:
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif", ".avif")):
                    src_file_path = os.path.join(root, file)
                    # Copy original file to testing/attack_samples/<category>/original_<file>
                    dest_cat_dir = os.path.join(BASE_TEMP, "attack_samples", category_label)
                    os.makedirs(dest_cat_dir, exist_ok=True)
                    dest_file_path = os.path.join(dest_cat_dir, f"orig_{file}")
                    
                    try:
                        shutil.copy2(src_file_path, dest_file_path)
                        all_records.append({
                            "original": file,
                            "transformed": f"orig_{file}",
                            "path": dest_file_path,
                            "transform": "original",
                            "category": category_label
                        })
                    except Exception as e:
                        print(f"[WARN] Failed to copy {src_file_path} to {dest_file_path}: {e}")
                        continue
                    
                    # Generate transformed variants
                    records = apply_transformations(src_file_path, file, category_label)
                    all_records.extend(records)
                    
    return all_records

def write_manifest(records):
    manifest_path = os.path.join(BASE_TEMP, "testing_manifest.md")

    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write("# AEGIS Testing Dataset Manifest\n\n")
        f.write("This manifest tracks all original images used in validation, along with their derived attack variants and edge cases.\n\n")
        f.write("| Original Image | Category | Transformed Name | Transform Applied | Path |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for r in records:
            f.write(f"| {r['original']} | {r['category']} | {r['transformed']} | {r['transform']} | {r['path']} |\n")
            
    # Also write a JSON file for easy programmatic access during test running
    import json
    with open(os.path.join(BASE_TEMP, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
        
    print(f"[INFO] Manifest written to {manifest_path} and {BASE_TEMP}/manifest.json")

def main():
    setup_directories()
    generate_synthetic_images()
    records = process_dataset()
    write_manifest(records)
    print("[SUCCESS] Test asset generation phase complete.")

if __name__ == "__main__":
    main()
