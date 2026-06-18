import os
import sys
import json
import hashlib
from PIL import Image
import numpy as np

# Ensure src is in PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))
from cli import main as cli_main

def run_cli(args_list):
    import io
    import contextlib
    old_argv = sys.argv
    sys.argv = ["cli.py"] + args_list
    stdout = io.StringIO()
    stderr = io.StringIO()
    returncode = 0
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            cli_main()
    except SystemExit as e:
        returncode = e.code if e.code is not None else 0
    except Exception as e:
        stderr.write(str(e))
        returncode = -1
    finally:
        sys.argv = old_argv
    return returncode, stdout.getvalue(), stderr.getvalue()

def test_copy_attack_detection():
    print("[INFO] Setting up copy attack detection test...")
    os.makedirs("testing/keys", exist_ok=True)
    
    # 1. Generate keys
    rc, stdout, stderr = run_cli(["keygen", "-o", "testing/keys"])
    assert rc == 0
    assert "keygen" in stdout or "successfully" in stdout
    
    priv_key_path = "testing/keys/aegis_private.pem"
    pub_key_path = "testing/keys/aegis_public.pem"
    assert os.path.exists(priv_path := priv_key_path)
    assert os.path.exists(pub_path := pub_key_path)
    
    # 2. Generate two distinct source images
    img1_path = "testing/generated_images/copy_source.png"
    img2_path = "testing/generated_images/copy_target.png"
    
    # Source Image 1: Gradient
    img1 = Image.new("RGB", (512, 512))
    pixels1 = img1.load()
    for x in range(512):
        for y in range(512):
            pixels1[x, y] = (x // 2, y // 2, 128)
    img1.save(img1_path)
    
    # Source Image 2: Noise / Stripes (structurally completely different)
    img2 = Image.new("RGB", (512, 512))
    pixels2 = img2.load()
    for x in range(512):
        for y in range(512):
            pixels2[x, y] = (255 - x // 2, 128, y // 2)
    img2.save(img2_path)
    
    # 3. Protect Image 1
    protected1_path = "testing/transformed_images/copy_source_protected.png"
    rc, stdout, stderr = run_cli([
        "protect", "-i", img1_path, "-o", protected1_path,
        "-m", "art", "-k", priv_key_path, "-w", "Owner-Jane", "--accept-ethics"
    ])
    assert rc == 0, f"Protect failed: {stdout} {stderr}"
    
    # 4. Verify Image 1 (Should pass)
    rc, stdout, stderr = run_cli(["verify", "-i", protected1_path, "-k", pub_key_path])
    assert rc == 0, f"Verify failed: {stdout} {stderr}"
    assert "WATERMARK DETECTED SUCCESSFULLY!" in stdout
    
    # 5. Extract difference/perturbation (simulating attacker copying DCT delta)
    orig_y = np.array(img1.convert("YCbCr"))[:,:,0].astype(np.float32)
    prot_y = np.array(Image.open(protected1_path).convert("YCbCr"))[:,:,0].astype(np.float32)
    delta_y = prot_y - orig_y
    
    # Apply delta_y to Image 2
    ycbcr2 = Image.open(img2_path).convert("YCbCr")
    channels2 = list(ycbcr2.split())
    y2_arr = np.array(channels2[0]).astype(np.float32)
    y2_prot = np.clip(y2_arr + delta_y, 0, 255).astype(np.uint8)
    channels2[0] = Image.fromarray(y2_prot)
    
    copied_path = "testing/transformed_images/copy_target_forged.png"
    Image.merge("YCbCr", tuple(channels2)).convert("RGB").save(copied_path)
    
    # 6. Verify Copied Image (Should detect Copy Attack and fail!)
    rc, stdout, stderr = run_cli(["verify", "-i", copied_path, "-k", pub_key_path])
    print("Verification result of copied image:")
    print(stdout)
    
    assert rc == 1
    assert "POTENTIAL COPY/REPLAY ATTACK DETECTED!" in stdout
    assert "Copy Attack detected" in stdout or "copy" in stdout.lower()
    
    # Clean up
    for p in [img1_path, img2_path, protected1_path, copied_path, priv_key_path, pub_key_path]:
        if os.path.exists(p):
            os.remove(p)
            
    print("[SUCCESS] Copy attack detection test passed successfully!")

if __name__ == "__main__":
    test_copy_attack_detection()
