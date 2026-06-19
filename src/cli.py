import argparse
import sys
import os
import binascii
import json
import hashlib
import hmac
from PIL import Image

try:
    import aegis_kernel
except ImportError:
    aegis_kernel = None

# Lazy-loaded components (loaded on-demand in main execution block)
ImageAnalyzer = None
PgdCloaker = None

# Define default log path
AUDIT_LOG_PATH = os.path.join(os.getcwd(), "aegis_audit.log")

def parse_seed(key_str: str) -> int:
    """Deterministic conversion of user key string to a u32 seed using SHA-256."""
    if os.path.exists(key_str):
        try:
            pub_key = load_or_derive_public_key(key_str)
            from cryptography.hazmat.primitives.asymmetric import ed25519
            from cryptography.hazmat.primitives import serialization
            if isinstance(pub_key, ed25519.Ed25519PublicKey):
                pub_bytes = pub_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )
                h = hashlib.sha256(pub_bytes).digest()
                return int.from_bytes(h[:4], byteorder="big") & 0xFFFFFFFF
        except Exception:
            pass
    h = hashlib.sha256(key_str.encode("utf-8")).digest()
    return int.from_bytes(h[:4], byteorder="big") & 0xFFFFFFFF

def load_or_derive_private_key(key_str: str):
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    if os.path.exists(key_str):
        try:
            with open(key_str, "rb") as f:
                data = f.read()
            return serialization.load_pem_private_key(data, password=None)
        except Exception:
            seed_bytes = hashlib.sha256(data).digest()
            return ed25519.Ed25519PrivateKey.from_private_bytes(seed_bytes)
    else:
        seed_bytes = hashlib.sha256(key_str.encode("utf-8")).digest()
        return ed25519.Ed25519PrivateKey.from_private_bytes(seed_bytes)

def load_or_derive_public_key(key_str: str):
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    if os.path.exists(key_str):
        try:
            with open(key_str, "rb") as f:
                data = f.read()
            return serialization.load_pem_public_key(data)
        except Exception:
            try:
                priv = serialization.load_pem_private_key(data, password=None)
                return priv.public_key()
            except Exception:
                seed_bytes = hashlib.sha256(data).digest()
                return ed25519.Ed25519PrivateKey.from_private_bytes(seed_bytes).public_key()
    else:
        seed_bytes = hashlib.sha256(key_str.encode("utf-8")).digest()
        return ed25519.Ed25519PrivateKey.from_private_bytes(seed_bytes).public_key()

def check_aegis_kernel():
    """Ensure the Rust kernel is built and available."""
    if aegis_kernel is None:
        print("\n[ERROR] The high-performance Rust DSP kernel ('aegis_kernel') is not installed or built.")
        print("Please build it first by running:")
        print("  venv/bin/maturin develop --manifest-path aegis_kernel/Cargo.toml --features python")
        print()
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="AEGIS: Anonymous Encryption & Generative Image Shield\n"
                    "Protects visual identity from AI models using a Python-Rust hybrid backend.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples of Usage:
  1. Apply hybrid protection (cloaking + watermark + frequency noise):
     python src/cli.py protect -i input.jpg -o protected.png -m hybrid -k 1337 -w '{"author": "Jane"}' --accept-ethics

  2. Verify and extract watermark ownership metadata from an image:
     python src/cli.py verify -i protected.png -k 1337

  3. Show the audit logs of past actions:
     python src/cli.py audit --lines 15
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available actions")

    # ================= COMMAND: protect =================
    protect_parser = subparsers.add_parser(
        "protect", 
        help="Apply cloaking and/or watermarking protection to an image",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Applies cryptographic watermarks and adversarial cloaking to shield images."
    )
    
    # Input/Output Group
    io_group = protect_parser.add_argument_group("Input / Output Options")
    io_group.add_argument("-i", "--input", required=True, help="Path to input image (JPG, PNG, etc.)")
    io_group.add_argument("-o", "--output", required=True, help="Path to save protected image (Should be .png)")
    
    # Protection Mode Group
    mode_group = protect_parser.add_argument_group("Protection Modes")
    mode_group.add_argument(
        "-m", "--mode", 
        choices=['art', 'face', 'hybrid'], 
        default='hybrid', 
        help="Protection mode:\n"
             "  art    - Applies frequency perturbation only (Rust DSP).\n"
             "  face   - Applies adversarial face cloaking only (PyTorch PGD).\n"
             "  hybrid - Applies both cloaking, frequency noise, and watermark (Default)."
    )
    mode_group.add_argument("-s", "--strength", type=float, default=5.0, help="Frequency noise perturbation strength (default: 5.0)")
    
    # Watermark Settings Group
    wm_group = protect_parser.add_argument_group("Watermarking Settings")
    wm_group.add_argument("-k", "--key", type=str, default="1337", help="Secret key/seed for watermark and shuffling (default: 1337)")
    wm_group.add_argument("-w", "--watermark", type=str, help="Watermark JSON metadata payload string (e.g. '{\"author\":\"Jane\"}')")
    wm_group.add_argument("--block-size", type=int, choices=[8, 16, 32, 64], default=8, help="Watermark block size (default: 8)")
    wm_group.add_argument("--robustness-level", choices=["standard", "aggressive"], default="standard", help="Robustness scaling level (default: standard)")
    
    # AI Cloaking Optimization Group
    ai_group = protect_parser.add_argument_group("Adversarial Cloaking Settings")
    ai_group.add_argument("--surrogate", choices=['mobilenet_v2', 'resnet18', 'mobilenet_v3_large'], default='mobilenet_v2', help="Surrogate CNN model (default: mobilenet_v2)")
    ai_group.add_argument("--eps", type=float, default=8.0, help="L-infinity perturbation budget in 0-255 scale (default: 8.0)")
    ai_group.add_argument("--steps", type=int, default=40, help="PGD optimization iterations (default: 40)")
    
    # Compliance & Safety Group
    safety_group = protect_parser.add_argument_group("Compliance & Safety Options")
    safety_group.add_argument("--offline", action="store_true", help="Force local model weights usage (do not download)")
    safety_group.add_argument("--accept-ethics", action="store_true", help="Acknowledge and accept the AEGIS Ethical Terms of Service")
    safety_group.add_argument("--json", action="store_true", help="Output raw JSON instead of log lines (useful for external scripts)")
    safety_group.add_argument("--override-warning", action="store_true", help="Bypass the interactive warning prompt for flagged images")

    # ================= COMMAND: verify =================
    verify_parser = subparsers.add_parser(
        "verify", 
        help="Verify and extract an embedded watermark from a protected image",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Extracts and decodes the hidden watermark payload using the secret key."
    )
    verify_parser.add_argument("-i", "--input", required=True, help="Path to protected image")
    verify_parser.add_argument("-k", "--key", type=str, default="1337", help="Secret numeric/text key used during embedding (default: 1337)")
    verify_parser.add_argument("--block-size", type=int, choices=[8, 16, 32, 64], default=8, help="Watermark block size (default: 8)")
    verify_parser.add_argument("--robustness-level", choices=["standard", "aggressive"], default="standard", help="Robustness scaling level (default: standard)")

    # ================= COMMAND: keygen =================
    keygen_parser = subparsers.add_parser(
        "keygen",
        help="Generate Ed25519 keypair for production watermark signing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Generates a pair of private and public PEM files for secure asymmetric watermarking."
    )
    keygen_parser.add_argument("-o", "--out-dir", default=".", help="Directory to save the keys (default: current directory)")

    # ================= COMMAND: audit =================
    audit_parser = subparsers.add_parser(
        "audit", 
        help="View the history of forensic audits and actions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Reads the local audit log file containing past operations."
    )
    audit_parser.add_argument("--lines", type=int, default=10, help="Number of recent log lines to display (default: 10)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # ---------------- EXECUTE: protect ----------------
    if args.command == "protect":
        if not args.accept_ethics:
            if args.json:
                print(json.dumps({"error": "Missing --accept-ethics flag"}))
            else:
                print("ERROR: You must explicitly pass --accept-ethics to acknowledge the AEGIS Acceptable Use Policy.")
            sys.exit(1)

        # Pre-validate input image file to prevent hangs/unnecessary overhead on corrupted files
        if not os.path.exists(args.input):
            if args.json:
                print(json.dumps({"error": f"Input file '{args.input}' not found"}))
            else:
                print(f"ERROR: Input file '{args.input}' not found.")
            sys.exit(1)

        try:
            with Image.open(args.input) as img:
                img.verify()
        except Exception as e:
            if args.json:
                print(json.dumps({"error": f"Invalid or corrupted image: {e}"}))
            else:
                print(f"ERROR: Input file '{args.input}' is not a valid or supported image. Details: {e}")
            sys.exit(1)

        # 1. Run ID-Guard Forensic Checks
        from aegis_core.analyzer import ImageAnalyzer
        analyzer = ImageAnalyzer()
        is_flagged, conf, reason = analyzer.check_id_guard(args.input)
        
        if is_flagged:
            if args.json:
                print(json.dumps({"flagged": True, "confidence": conf, "reason": reason}))
                if not args.override_warning:
                    sys.exit(0)
            else:
                print(f"\n[!] AEGIS SECURITY WARNING [!]")
                print(f"Forensic analyzer flagged image. Reason: {reason} (Confidence: {conf*100:.1f}%)")
                print("WARNING: Obfuscating official identification systems is strictly prohibited.")
                
                if not args.override_warning:
                    override = input("Are you absolutely sure you want to proceed? (yes/no): ")
                    if override.lower() != 'yes':
                        print("Operation aborted by user.")
                        sys.exit(0)
            analyzer.log_operation(args.input, "OVERRIDE", f"User overrode warning: {reason}")
        elif args.json:
            print(json.dumps({"flagged": False, "confidence": conf, "reason": "Clean"}))

        # Ensure output is PNG to preserve high-frequency details
        if not args.output.lower().endswith(".png"):
            if not args.json:
                print("[WARN] Output file does not end in '.png'. Lossy formats (like .jpg) will corrupt the watermark/cloaking.")
                print("Enforcing output format as PNG...")
            args.output = os.path.splitext(args.output)[0] + ".png"

        # 2. Step A: Apply PyTorch PGD Cloaking (if face or hybrid)
        current_img_path = args.input
        temp_cloaked_path = None
        
        if args.mode in ['face', 'hybrid']:
            if not args.json:
                print(f"[*] Applying adversarial face cloaking using {args.surrogate}...")
            
            from aegis_core.cloaking import PgdCloaker
            cloaker = PgdCloaker(surrogate_name=args.surrogate, offline=args.offline)
            safe_steps = min(max(1, args.steps), 250)
            safe_eps = min(max(0.0, args.eps), 255.0)
            cloaked_img = cloaker.cloak_image(args.input, eps=safe_eps, steps=safe_steps)
            
            # Save cloaked image temporarily to be processed by Rust if needed, or save directly
            if args.mode == 'hybrid':
                temp_cloaked_path = args.output + ".tmp.png"
                cloaked_img.save(temp_cloaked_path, format="PNG")
                current_img_path = temp_cloaked_path
            else:
                cloaked_img.save(args.output, format="PNG")
                if not args.json:
                    print(f"[SUCCESS] Shielded image saved to {args.output}")
                analyzer.log_operation(args.input, "PROTECT", f"Applied face cloaking. Saved to {args.output}")

        # 3. Step B: Apply Rust DSP operations (if art or hybrid)
        if args.mode in ['art', 'hybrid']:
            check_aegis_kernel()
            if not args.json:
                print(f"[*] Applying Rust frequency perturbations (strength={args.strength})...")
            
            img = Image.open(current_img_path).convert("RGB")
            width, height = img.size
            
            # Convert to YCbCr to manipulate the Y (luminance) channel in Rust
            ycbcr = img.convert("YCbCr")
            y_chan, cb_chan, cr_chan = ycbcr.split()
            y_bytes = list(y_chan.tobytes())
            seed = parse_seed(args.key)

            # Frequency perturbation
            y_bytes = aegis_kernel.perturb_frequency_py(
                y_bytes, width, height, args.strength, seed
            )
            
            # Watermark embedding (if payload is provided or if hybrid mode needs default watermark)
            payload = args.watermark
            if args.mode == 'hybrid' and not payload:
                # If hybrid mode, default to a standard ownership JSON string
                payload = json.dumps({"protected_by": "AEGIS Image Shield"})
                
            if payload:
                if not args.json:
                    print(f"[*] Embedding invisible watermark...")
                try:
                    # Calculate aHash of the image
                    try:
                        resample_filter = Image.Resampling.LANCZOS
                    except AttributeError:
                        resample_filter = Image.LANCZOS
                    small_img = img.convert("L").resize((8, 8), resample_filter)
                    pixels = list(small_img.getdata())
                    avg = sum(pixels) / 64
                    bits = "".join(["1" if p >= avg else "0" for p in pixels])
                    img_hash = f"{int(bits, 2):016x}"

                    # Asymmetric signing via Ed25519
                    private_key = load_or_derive_private_key(args.key)
                    message_to_sign = f"{payload}|{img_hash}".encode("utf-8")
                    signature_bytes = private_key.sign(message_to_sign)
                    sig_hex = signature_bytes.hex()

                    wrapped_payload = json.dumps({
                        "payload": payload,
                        "image_hash": img_hash,
                        "signature": sig_hex
                    })
                    delta = 80.0 if args.robustness_level == "aggressive" else 40.0
                    y_bytes = aegis_kernel.embed_watermark_py(
                        y_bytes, width, height, wrapped_payload, seed, delta, args.block_size
                    )
                except ValueError as e:
                    print(f"[ERROR] Watermark embedding failed: {e}")
                    if temp_cloaked_path and os.path.exists(temp_cloaked_path):
                        os.remove(temp_cloaked_path)
                    sys.exit(1)

            # Reconstruct and merge back
            new_y_chan = Image.frombytes("L", (width, height), bytes(y_bytes))
            final_img = Image.merge("YCbCr", (new_y_chan, cb_chan, cr_chan)).convert("RGB")
            final_img.save(args.output, format="PNG")
            
            # Clean up temp file
            if temp_cloaked_path and os.path.exists(temp_cloaked_path):
                os.remove(temp_cloaked_path)
                
            if not args.json:
                print(f"[SUCCESS] Protected image saved to {args.output}")
            analyzer.log_operation(args.input, "PROTECT", f"Applied Rust frequency/watermark. Saved to {args.output}")

    # ---------------- EXECUTE: verify ----------------
    elif args.command == "verify":
        check_aegis_kernel()
        print(f"[*] Scanning {args.input} for invisible watermark...")
        
        if not os.path.exists(args.input):
            print(f"[ERROR] Input file not found: {args.input}")
            sys.exit(1)

        try:
            with Image.open(args.input) as img:
                img.verify()
        except Exception as e:
            print(f"[ERROR] Input file '{args.input}' is not a valid or supported image. Details: {e}")
            sys.exit(1)
            
        try:
            img = Image.open(args.input).convert("RGB")
            width, height = img.size
            ycbcr = img.convert("YCbCr")
            y_chan, _, _ = ycbcr.split()
            y_bytes = list(y_chan.tobytes())
            seed = parse_seed(args.key)
            
            delta = 80.0 if args.robustness_level == "aggressive" else 40.0
            payload_raw = aegis_kernel.detect_watermark_py(
                y_bytes, width, height, seed, args.block_size, delta
            )
            data = json.loads(payload_raw)
            if not isinstance(data, dict) or "payload" not in data or "signature" not in data:
                raise ValueError("Watermark signature format invalid or missing")
            
            payload = data["payload"]
            
            if "image_hash" in data:
                embedded_hash = data["image_hash"]
                sig_hex = data["signature"]

                # Verify Ed25519 signature
                public_key = load_or_derive_public_key(args.key)
                message_to_verify = f"{payload}|{embedded_hash}".encode("utf-8")
                try:
                    public_key.verify(bytes.fromhex(sig_hex), message_to_verify)
                except Exception:
                    raise ValueError("Watermark signature verification failed (forgery/overwriting detected)")

                # Verify copy/replay attack using aHash Hamming distance
                try:
                    resample_filter = Image.Resampling.LANCZOS
                except AttributeError:
                    resample_filter = Image.LANCZOS
                current_small = img.convert("L").resize((8, 8), resample_filter)
                current_pixels = list(current_small.getdata())
                current_avg = sum(current_pixels) / 64
                current_bits = "".join(["1" if p >= current_avg else "0" for p in current_pixels])
                current_hash = f"{int(current_bits, 2):016x}"

                dist = bin(int(embedded_hash, 16) ^ int(current_hash, 16)).count("1")
                if dist > 10:
                    print("\n========================================")
                    print("[WARNING] POTENTIAL COPY/REPLAY ATTACK DETECTED!")
                    print("========================================")
                    print(f"The watermark signature is valid, but the image content has been altered or copied.")
                    print(f"Hamming distance: {dist} bits (Threshold: 10 bits)")
                    print(f"Embedded Hash: {embedded_hash}")
                    print(f"Current Hash:  {current_hash}")
                    print("========================================")
                    raise ValueError("Watermark matches owner signature but content mismatch (Copy Attack detected)")

                print("\n========================================")
                print("[SUCCESS] WATERMARK DETECTED SUCCESSFULLY!")
                print("========================================")
                print(f"Decoded Payload: {payload}")
                print(f"Image Bind Hash: {embedded_hash}")
                print("========================================")
            else:
                raise ValueError("Watermark signature verification failed (missing image bind hash)")
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            print("\n========================================")
            print("[FAILED] No valid watermark detected.")
            print(f"Reason: Watermark verification failed (payload is not signed or corrupted): {e}")
            print("========================================")
            sys.exit(1)
        except ValueError as e:
            print("\n========================================")
            print("[FAILED] No valid watermark detected.")
            print(f"Reason: {e}")
            print("========================================")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Verification failed: {e}")
            sys.exit(1)

    # ---------------- EXECUTE: keygen ----------------
    elif args.command == "keygen":
        os.makedirs(args.out_dir, exist_ok=True)
        priv_path = os.path.join(args.out_dir, "aegis_private.pem")
        pub_path = os.path.join(args.out_dir, "aegis_public.pem")

        from cryptography.hazmat.primitives.asymmetric import ed25519
        from cryptography.hazmat.primitives import serialization

        private_key = ed25519.Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        with open(priv_path, "wb") as f:
            f.write(private_pem)
        with open(pub_path, "wb") as f:
            f.write(public_pem)

        print(f"[SUCCESS] Ed25519 keypair generated successfully:")
        print(f"  Private Key: {priv_path}")
        print(f"  Public Key:  {pub_path}")

    # ---------------- EXECUTE: audit ----------------
    elif args.command == "audit":
        print(f"[*] Retrieving recent audit logs (last {args.lines} lines):\n")
        if not os.path.exists(AUDIT_LOG_PATH):
            print("No audit log file found. Execute a protection command first.")
            sys.exit(0)
            
        try:
            with open(AUDIT_LOG_PATH, "r") as f:
                lines = f.readlines()
                for line in lines[-args.lines:]:
                    print(line.strip())
        except Exception as e:
            print(f"[ERROR] Failed to read audit log: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
