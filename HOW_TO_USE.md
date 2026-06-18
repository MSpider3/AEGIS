# How to Use AEGIS CLI

AEGIS (Anonymous Encryption & Generative Image Shield) is now configured as a high-performance **Python Command Line Interface (CLI)** powered by a split Python/Rust backend. 

Follow this guide to set up the tool, protect your images, and verify watermarks.

---

## 🛠️ Step 1: Installation & Setup

1. **Set up your Python virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Run the smart installer**:
   The installer detects your OS and GPU hardware (NVIDIA CUDA, Apple Silicon MPS, or standard CPU) to install the correct PyTorch wheels before loading other requirements:
   ```bash
   venv/bin/python install_libraries.py
   ```

3. **Build the Rust DSP kernel bindings**:
   Compile the underlying DCT and watermarking algorithms into your virtual environment:
   ```bash
   VIRTUAL_ENV=venv venv/bin/pip install maturin
   VIRTUAL_ENV=venv venv/bin/maturin develop --manifest-path aegis_kernel/Cargo.toml --features python
   ```

---

## 🔑 Step 2: Generating Keypairs (`keygen` command)

Generate an Ed25519 asymmetric private/public keypair to securely sign and verify watermarks:

```bash
PYTHONPATH=src venv/bin/python src/cli.py keygen -o keys/
```
* **Output**: This generates two files: `keys/aegis_private.pem` (your private signing key) and `keys/aegis_public.pem` (your public verification key). Keep the private key secure and private!

---

## 🛡️ Step 3: Protecting Images (`protect` command)

The `protect` command scans your image through the ID-Guard compliance gatekeeper and applies the requested protection modes.

### Example: Asymmetric Hybrid Protection (Production Recommended)
```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i original_portrait.jpg \
  -o protected_portrait.png \
  -m hybrid \
  -k keys/aegis_private.pem \
  -w '{"author": "Jane Doe", "copyright": "2026", "license": "CC-BY-NC"}' \
  --accept-ethics
```

### Example: Symmetric Key Protection (Backward Compatible)
```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i original_portrait.jpg \
  -o protected_portrait.png \
  -m hybrid \
  -k 9876 \
  -w '{"author": "Jane Doe"}' \
  --accept-ethics
```

### Parameter Details
* **`-i` / `--input`**: Path to the original source image.
* **`-o` / `--output`**: Path to write the shielded image. **Always use a `.png` file extension**; saving as `.jpg` or other lossy formats compresses and corrupts the protection layers.
* **`-m` / `--mode`**:
  * `hybrid` (Default): Runs PyTorch face cloaking first, then applies Rust frequency noise and embeds the Rust watermark. Highly recommended for portraits.
  * `face`: Runs PyTorch face cloaking only. Best for quick face protection.
  * `art`: Runs Rust frequency noise and watermark embedding. Ideal for digital art and landscapes.
* **`-k` / `--key`**: Path to an Ed25519 PEM key file or a numeric/text seed.
* **`-w` / `--watermark`**: A JSON string containing owner metadata.
* **`--accept-ethics`**: Required flag acknowledging that you are not obfuscating official government IDs or documents.

---

## 🔍 Step 4: Verifying Watermarks (`verify` command)

Scan an image, decrypt the watermark, and check for copy/replay attacks.

### Example: Asymmetric Key Verification (Production Recommended)
Use your **public key** to verify ownership:
```bash
PYTHONPATH=src venv/bin/python src/cli.py verify \
  -i protected_portrait.png \
  -k keys/aegis_public.pem
```

### Example: Symmetric Key Verification (Backward Compatible)
```bash
PYTHONPATH=src venv/bin/python src/cli.py verify \
  -i protected_portrait.png \
  -k 9876
```

### Verification Outputs
* **On Success**: The CLI prints a success message and displays your decoded JSON payload.
* **On Copy-Attack**: If the watermark was copied from another cover image, the verification succeeds but prints a prominent warning: `[WARNING] POTENTIAL COPY/REPLAY ATTACK DETECTED!`.
* **On Failure**: Mismatched keys or corrupted payloads fail verification.

---

## 📋 Step 5: Checking Log History (`audit` command)

For auditing and transparency, AEGIS logs all operations in a local persistent log file named `aegis_audit.log`. You can retrieve entries using the `audit` command:

```bash
# Display the last 15 actions
PYTHONPATH=src venv/bin/python src/cli.py audit --lines 15
```

---

## 🧪 Step 6: Running Quality Assurance Validation

To run the complete suite of 14 isolated quality assurance, fuzzing, and safety checks:

```bash
PYTHONPATH=src venv/bin/python testing/run_audit.py
```
This script runs tests from `testing/test_scripts/` and writes a compiled executive report to `testing/audit_report_production.md`.

---

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'aegis_kernel'"
* **Fix**: Ensure your virtual environment is active (`source venv/bin/activate`) and run:
  ```bash
  VIRTUAL_ENV=venv venv/bin/maturin develop --manifest-path aegis_kernel/Cargo.toml --features python
  ```

### Lossy Compression Warnings
* Always store protected outputs as lossless PNGs. Lossy JPEG compression discards high-frequency pixel changes, which destroys the adversarial cloaking noise and ruins the watermark.
