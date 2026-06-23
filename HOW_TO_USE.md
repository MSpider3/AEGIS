# How to Use AEGIS CLI: Operations & Scenario Guide

AEGIS (Anonymous Encryption & Generative Image Shield) is a command-line utility powered by a hybrid Python/Rust backend. This guide details how to install the system, generate cryptographic keys, and use the CLI under various protection and verification scenarios.

---

## 📌 Table of Contents
1. [🛠️ Installation & Setup](#-installation--setup)
2. [🔑 Keypair Generation (`keygen`)](#-keypair-generation-keygen)
3. [🛡️ Shielding Images (`protect`): Situation-Specific Examples](#-shielding-images-protect-situation-specific-examples)
   - [Situation A: Protecting Portrait/Selfie Images (Biometric Scraping Protection)](#situation-a-protecting-portraitselfie-images-biometric-scraping-protection)
   - [Situation B: Protecting Digital Artwork & Style Mimicry (No Faces)](#situation-b-protecting-digital-artwork--style-mimicry-no-faces)
   - [Situation C: Full Hybrid Protection (Maximum Security for Portraits)](#situation-c-full-hybrid-protection-maximum-security-for-portraits)
   - [Situation D: Inserting Custom Cryptographic Watermarks (Forensic Tracking)](#situation-d-inserting-custom-cryptographic-watermarks-forensic-tracking)
   - [Situation E: Automated Batch Processing & Integration Scripts](#situation-e-automated-batch-processing--integration-scripts)
   - [Situation F: Offline & Air-Gapped Environments](#situation-f-offline--air-gapped-environments)
4. [🔍 Verifying Watermarks (`verify`): Situation-Specific Examples](#-verifying-watermarks-verify-situation-specific-examples)
   - [Situation A: Verifying a Standard QIM-Frequency Watermark](#situation-a-verifying-a-standard-qim-frequency-watermark)
   - [Situation B: Verifying a Legacy Watermarked Image](#situation-b-verifying-a-legacy-watermarked-image)
   - [Situation C: Forensic Audit and Copy-Attack Detection](#situation-c-forensic-audit-and-copy-attack-detection)
5. [📋 Logging & Auditing (`audit` command)](#-logging--auditing-audit-command)
6. [🧪 Running Quality Assurance Validation](#-running-quality-assurance-validation)
7. [🎛️ Parameters Reference Guide](#-parameters-reference-guide)
8. [💡 Best Practices for Watermark Integrity](#-best-practices-for-watermark-integrity)
9. [🐳 Containerized Execution with Podman](#-containerized-execution-with-podman)

---

## 🛠️ Installation & Setup

Before running AEGIS, initialize your virtual environment, install hardware-specific deep learning libraries, and compile the high-performance Rust DSP kernel.

### 1. Initialize Virtual Environment
```bash
python3 -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows (Command Prompt)
venv\Scripts\activate.bat
# Windows (PowerShell)
.\venv\Scripts\Activate.ps1
```

### 2. Smart Library Installer
Run the hardware detector. This script determines if your system has an NVIDIA GPU (CUDA), Apple Silicon GPU (Metal/MPS), or only CPU, and configures PyTorch accordingly:
```bash
venv/bin/python install_libraries.py
```

### 3. Compile Rust DSP Kernel
Install `maturin` and compile the optimized Rust discrete cosine transform (DCT) bindings directly into your virtual environment:
```bash
VIRTUAL_ENV=venv venv/bin/pip install maturin
VIRTUAL_ENV=venv venv/bin/maturin develop --manifest-path aegis_kernel/Cargo.toml --features python
```

### 4. Alternative: Running Containerized with Podman
If you prefer not to install Python, Rust, and system libraries directly on your host machine, you can run all AEGIS commands inside a container. For a detailed guide on container usage, volume mounting, and directory mapping, refer to the [🐳 Containerized Execution with Podman](#-containerized-execution-with-podman) section.

---

## 🔑 Keypair Generation (`keygen`)

AEGIS uses **Ed25519 asymmetric cryptography**. Owners sign watermarks with a private key, and anyone can verify ownership using the corresponding public key.

### Example: Generate keys in a specific directory
```bash
PYTHONPATH=src venv/bin/python src/cli.py keygen -o keys/
```
* **Output**:
  * `keys/aegis_private.pem`: Your private signing key (Keep this secure and secret!).
  * `keys/aegis_public.pem`: Your public verification key (Distribute to platforms/verifiers).

---

## 🛡️ Shielding Images (`protect`): Situation-Specific Examples

The `protect` command runs the input through the automated **ID-Guard** forensic gatekeeper (checking for passports/driver's licenses) and applies cloaking and watermarking. 

> [!IMPORTANT]
> **Always output to lossless `.png` format.** Saving as `.jpg`, `.webp`, or other lossy formats runs compression algorithms that discard high-frequency data, ruining the adversarial noise and the watermark.

### Situation A: Protecting Portrait/Selfie Images (Biometric Scraping Protection)
Use these configurations when you want to protect your personal face photographs from being indexed by facial recognition scrapers (e.g. Clearview AI).

#### 1. Standard Cloaking (Fastest, optimized for mobile surrogates)
Uses a lightweight MobileNetV2 architecture. Best for fast processing on lower-end systems:
```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i my_face.jpg \
  -o shielded_face.png \
  -m face \
  --surrogate mobilenet_v2 \
  --accept-ethics
```

#### 2. Robust Cloaking (Recommended, target surrogate CNN)
Uses a ResNet18 architecture, providing higher adversarial transferability to other models:
```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i my_face.jpg \
  -o shielded_face.png \
  -m face \
  --surrogate resnet18 \
  --accept-ethics
```

#### 3. Maximum-Security Cloaking (Aggressive perturbation budget)
Increases the L-infinity budget ($\epsilon$) and the number of PGD optimization steps. Highly effective against hardened classifiers:
```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i my_face.jpg \
  -o shielded_face.png \
  -m face \
  --surrogate resnet18 \
  --eps 16.0 \
  --steps 80 \
  --accept-ethics
```

---

### Situation B: Protecting Digital Artwork & Style Mimicry (No Faces)
Use these configurations when you are an artist posting illustrations, concept art, or paintings online, and want to prevent generative AI scrapers from digesting your artistic style.

#### 1. Standard Style Protection (Art Mode)
Applies mid-frequency DCT perturbations using the Rust DSP kernel. Skips the deep learning face-cloaking step completely (saving CPU/GPU cycles):
```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i digital_painting.jpg \
  -o protected_art.png \
  -m art \
  -k keys/aegis_private.pem \
  -w '{"author": "Jane Doe", "license": "CC-BY-NC"}' \
  --accept-ethics
```

#### 2. Aggressive Style Perturbation (Heavy Frequency Noise)
Increases the frequency noise strength (`-s`) to introduce stronger high-frequency disruption:
```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i digital_painting.jpg \
  -o protected_art.png \
  -m art \
  -s 12.0 \
  -k keys/aegis_private.pem \
  -w '{"author": "Jane Doe"}' \
  --accept-ethics
```

---

### Situation C: Full Hybrid Protection (Maximum Security for Portraits)
Recommended for posting high-quality portraits or artist profiles where both biometric indexing protection (cloaking) and ownership tracking (watermark) are desired.

```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i original_portrait.jpg \
  -o protected_portrait.png \
  -m hybrid \
  -k keys/aegis_private.pem \
  -w '{"author": "Jane Doe", "copyright": "2026", "allow_derivatives": false}' \
  --surrogate resnet18 \
  --eps 10.0 \
  --steps 50 \
  --watermark-engine qim-frequency \
  --block-size 16 \
  --robustness-level aggressive \
  --accept-ethics
```

---

### Situation D: Inserting Custom Cryptographic Watermarks (Forensic Tracking)
Use these options when you want to embed a hidden ownership stamp that is bound to the image structures to prevent copy/paste spoofing.

#### 1. Standard Frequency Watermark (Block Size 8x8)
Fast watermark insertion using standard block-level DCT partitioning:
```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i input.png \
  -o watermarked_standard.png \
  -m art \
  -k keys/aegis_private.pem \
  -w '{"owner_id": "USR-99812", "timestamp": 178201201}' \
  --watermark-engine qim-frequency \
  --block-size 8 \
  --robustness-level standard \
  --accept-ethics
```

#### 2. Max-Survivability Watermark (Aggressive QIM, large blocks)
Forces a larger grid size (e.g. 16x16 or 32x32 blocks) and aggressive quantization scaling to make the watermark highly resistant to cropping, scaling, and heavy noise:
```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i input.png \
  -o watermarked_robust.png \
  -m art \
  -k keys/aegis_private.pem \
  -w '{"org": "AEGIS-Security", "hash_verify": true}' \
  --watermark-engine qim-frequency \
  --block-size 16 \
  --robustness-level aggressive \
  --accept-ethics
```

#### 3. Legacy Watermark (Backward compatibility)
Uses the legacy symmetric frequency watermarking engine (pre-asymmetric upgrade):
```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i input.png \
  -o watermarked_legacy.png \
  -m art \
  -k 9876 \
  -w '{"author": "Legacy User"}' \
  --watermark-engine legacy \
  --accept-ethics
```

---

### Situation E: Automated Batch Processing & Integration Scripts
Use these arguments when you are integrating AEGIS into a batch script or backend daemon. This bypasses interactive confirmation prompts and returns parseable JSON output instead of developer logs.

#### Example: Processing a directory of images via python script
```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i raw_image.png \
  -o batch_output.png \
  -m hybrid \
  -k keys/aegis_private.pem \
  -w '{"batch": "442"}' \
  --override-warning \
  --json \
  --accept-ethics
```
* **Output Format**:
  ```json
  {"flagged": false, "confidence": 0.0, "reason": "Clean"}
  ```

---

### Situation F: Offline & Air-Gapped Environments
By default, PyTorch may attempt to verify or download model weights online. Use the `--offline` flag to restrict surrogate model loading to locally cached weights on your air-gapped system.

```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i input.png \
  -o protected_offline.png \
  -m face \
  --offline \
  --accept-ethics
```

---

## 🔍 Verifying Watermarks (`verify`): Situation-Specific Examples

The `verify` command extracts the hidden payload, validates the Ed25519 signature using the public key, and computes structural image compatibility to detect copy-attacks.

### Situation A: Verifying a Standard QIM-Frequency Watermark
Verify a modern image using the owner's public key:
```bash
PYTHONPATH=src venv/bin/python src/cli.py verify \
  -i protected_portrait.png \
  -k keys/aegis_public.pem \
  --watermark-engine qim-frequency \
  --block-size 16 \
  --robustness-level aggressive
```

### Situation B: Verifying a Legacy Watermarked Image
Verify an image protected with a numeric seed using the legacy engine:
```bash
PYTHONPATH=src venv/bin/python src/cli.py verify \
  -i watermarked_legacy.png \
  -k 9876 \
  --watermark-engine legacy
```

### Situation C: Forensic Audit and Copy-Attack Detection
If a bad actor extracts the watermark coordinates from your image and attempts to re-apply (paste) it onto another cover image, the verification engine will automatically catch this:
```bash
PYTHONPATH=src venv/bin/python src/cli.py verify \
  -i suspicious_forgery.png \
  -k keys/aegis_public.pem \
  --watermark-engine qim-frequency \
  --block-size 16 \
  --robustness-level aggressive
```
* **Analysis**: The script recovers the original payload and checks the visual Average Hash (aHash) signature. If the cover image features do not match, the console outputs:
  ```text
  ========================================
  [WARNING] POTENTIAL COPY/REPLAY ATTACK DETECTED!
  ========================================
  The watermark signature is valid, but the image content has been altered or copied.
  Hamming distance: 24 bits (Threshold: 10 bits)
  Embedded Hash: dcdcdcdcdcdcdcdc
  Current Hash:  786a345bf923a109
  ========================================
  ```

---

## 📋 Logging & Auditing (`audit` command)

AEGIS writes all operations (actions, timestamps, paths, ID-Guard overrides, etc.) to a local file `aegis_audit.log`. Use the `audit` command to query it:

```bash
# Print the last 20 operations
PYTHONPATH=src venv/bin/python src/cli.py audit --lines 20
```

---

## 🧪 Running Quality Assurance Validation

To run the complete automated test suite verifying cryptographics, Rust memory safety, ID-Guard detection rates, and regression metrics:

```bash
PYTHONPATH=src venv/bin/python testing/run_audit.py
```

---

## 🎛️ Parameters Reference Guide

### `protect` command options

| Argument | Choices / Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `-i`, `--input` | Filepath | *(Required)* | Path to the source image (JPG, PNG, BMP, etc.). |
| `-o`, `--output` | Filepath | *(Required)* | Output path. **Must be a .png** to preserve pixel values. |
| `-m`, `--mode` | `art`, `face`, `hybrid` | `hybrid` | Protection mode configuration. |
| `-s`, `--strength` | Float | `5.0` | Rust DSP mid-frequency noise strength (for style perturbation). |
| `-k`, `--key` | String / Filepath | `1337` | Secret key. Can be a seed, password, or path to a private PEM. |
| `-w`, `--watermark`| JSON String | `None` | Payload metadata to embed in the Y-channel. |
| `--block-size` | `8`, `16`, `32`, `64` | `8` | Size of DCT blocks during frequency modulation. |
| `--robustness-level`| `standard`, `aggressive`| `standard` | Controls the delta quantizer size for watermark strength. |
| `--surrogate` | `mobilenet_v2`, `resnet18` | `mobilenet_v2` | Surrogate network used to compute backpropagation gradients. |
| `--eps` | Float (0.0 to 255.0) | `8.0` | Perturbation constraint (L-infinity radius). |
| `--steps` | Integer | `40` | Projected Gradient Descent iterations. |
| `--offline` | *(Flag)* | `False` | Forces PGD and models to load local weight checkpoints. |
| `--accept-ethics` | *(Flag)* | `False` | Confirms user compliance with AEGIS Ethical Guidelines. |
| `--override-warning`| *(Flag)* | `False` | Bypasses interactive confirmation prompts on flagged images. |
| `--json` | *(Flag)* | `False` | Outputs logs and status outputs in parseable JSON. |

### `verify` command options

| Argument | Choices / Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `-i`, `--input` | Filepath | *(Required)* | Path to the protected PNG image. |
| `-k`, `--key` | String / Filepath | `1337` | Path to public PEM key or symmetric seed used during protection. |
| `--block-size` | `8`, `16`, `32`, `64` | `8` | Must match the block size parameter used during embedding. |
| `--robustness-level`| `standard`, `aggressive`| `standard` | Must match the robustness profile used during embedding. |

---

## 💡 Best Practices for Watermark Integrity

To ensure that your invisible watermark can always be successfully extracted and verified:
1. **Never Save as JPG/JPEG**: Standard JPEGs run lossy high-frequency quantization, which destroys the micro-modulations introduced by QIM.
2. **Preserve Aspect Ratio**: If you must resize the protected image, scale it proportionally. Non-uniform stretching can misalign the DCT grid.
3. **Use Aggressive Profile for Web Uploads**: If you plan to post your protected image to social media platforms that run automated compression algorithms, protect the image using `--robustness-level aggressive` and `--block-size 16`.

---

## 🐳 Containerized Execution with Podman

AEGIS can be run in a completely containerized manner using Podman. This isolates Python and system dependencies like Tesseract OCR, while permitting cryptographic signing keys and images to reside on the host filesystem via volume mounts.

### 1. Build the Container Image
Ensure you have Podman installed and run the following command in the root directory:
```bash
podman build -t aegis:latest .
```

### 2. Volume Mounting & SELinux Relabeling (`:Z`)
When running containers rootless on Linux, Podman needs access to directories containing keys and images.
We use the `-v` (volume mount) flag in the format `-v /host/path:/container/path:Z`.
The `:Z` flag tells Podman to automatically relabel the directory's SELinux security context so that the container has permission to read and write to the host paths.

### 3. Execution Commands & Scenarios

#### Scenario A: Generating Keys (`keygen`)
To generate Ed25519 public/private keys and write them to the host directory `./keys`:
```bash
podman run --rm -it \
  -v ./keys:/keys:Z \
  aegis:latest keygen -o /keys
```

#### Scenario B: Protecting an Image (`protect`)
To apply hybrid protection on an image, mounting a host directory `./images` for input and output files, and `./keys` for the private key:
```bash
podman run --rm -it \
  -v ./keys:/keys:Z \
  -v ./images:/images:Z \
  aegis:latest protect \
  -i /images/original_portrait.jpg \
  -o /images/protected_portrait.png \
  -m hybrid \
  -k /keys/aegis_private.pem \
  -w '{"author": "Jane Doe", "copyright": "2026"}' \
  --accept-ethics
```

#### Scenario C: Verifying a Protected Image (`verify`)
To extract and verify the watermark from a protected image:
```bash
podman run --rm -it \
  -v ./keys:/keys:Z \
  -v ./images:/images:Z \
  aegis:latest verify \
  -i /images/protected_portrait.png \
  -k /keys/aegis_public.pem
```

#### Scenario D: Querying Audit Logs (`audit`)
To persist the audit log on the host, you can mount a file to map `/app/aegis_audit.log`:
```bash
podman run --rm -it \
  -v ./aegis_audit.log:/app/aegis_audit.log:Z \
  aegis:latest audit --lines 10
```

