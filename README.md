# AEGIS: Anonymous Encryption & Generative Image Shield

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![Rust Toolchain](https://img.shields.io/badge/Rust-1.70%2B-orange)](https://www.rust-lang.org/)
[![System Status](https://img.shields.io/badge/Status-Production%20Ready-success)](REPORT.md)
[![Coverage](https://img.shields.io/badge/Coverage-93.93%25-brightgreen)](REPORT.md)

AEGIS is a production-grade, offline, high-performance image protection tool designed to shield personal portraits, illustrations, and digital artwork from unauthorized AI training, facial recognition indexing, and web scraping. 

By combining PyTorch-based adversarial face cloaking with a custom compiled Rust DSP engine for invisible Y-channel watermarking, AEGIS acts as an imperceptible, cryptographically secure shield for your digital identity and intellectual property.

---

## 📌 Table of Contents

- [💡 AEGIS in a Nutshell](#-aegis-in-a-nutshell)
- [🚀 Key Features](#-key-features)
- [📁 Repository Structure](#-repository-structure)
- [💻 System Requirements](#-system-requirements)
- [📦 Installation Guide](#-installation-guide)
- [🛡️ Commands & Usage Examples](#-commands--usage-examples)
- [🧪 Quality Assurance & Security Validation](#-quality-assurance--security-validation)
- [⚖️ Ethics & Compliance](#-ethics--compliance)
- [🔒 Security Policy & Threat Model](#-security-policy--threat-model)
- [🔧 Troubleshooting](#-troubleshooting)
- [🤝 Contributing](#-contributing)
- [📄 License & Trademarks](#-license--trademarks)
- [👥 Support & Feedback](#-support--feedback)

---

## 💡 AEGIS in a Nutshell

Imagine you post a picture of your face or your artwork online. AI programs can automatically copy your image to train AI generators, and facial recognition systems can scan it to track you. 

AEGIS is a tool that helps you protect your images from being used by these AI systems without your permission. It does this in two main ways:

1. **A Confusing Trick for AI (Image Cloaking)**: AEGIS makes tiny, microscopic adjustments to your image. To a human, the image looks exactly the same. But to an AI, these tiny changes act like a visual optical illusion. When an AI tries to scan your face or copy your drawing style, it gets completely confused and sees only scrambled gibberish. This prevents AI models from learning from or copying your images.
2. **An Invisible Ownership Stamp (Digital Watermark)**: AEGIS hides a unique digital signature deep inside the image. You cannot see this signature, but it is locked into the picture. Even if someone takes a screenshot, crops the image, or compresses it to post online, the signature remains. Using a matching digital key, you can always prove that you are the original owner of the image.

In short, AEGIS lets you post your photos and artwork online while making sure AI systems cannot read or steal them.

---

## 🚀 Key Features

* **Adversarial Face Cloaking**: Leverages Projected Gradient Descent (PGD) optimization against deep learning models (MobileNet, ResNet) to disrupt facial feature extraction while keeping modifications visually imperceptible.
* **Production-Grade Asymmetric Cryptography (Ed25519)**: Replaced symmetric HMAC keys with **Ed25519 asymmetric signatures**. Owners sign watermarks with a private key, and external platforms/verifiers validate ownership integrity using the public key.
* **Copy-Attack Prevention (Perceptual aHash Binding)**: Binds the watermark payload to the cover image's structure using an Average Hash (aHash) fingerprint. Verifiers automatically detect and reject watermarks replayed or copied onto different images.
* **Mid-Frequency DSP Majority-Voting (Rust)**: Employs a compiled Rust core to perform Discrete Cosine Transform (DCT) block manipulations. Uses a secure **ChaCha8 stream cipher** for coordinate mapping and payload encryption, with block majority-voting for error-tolerant watermark extraction.
* **Ethical ID-Guard Compliance**: Built-in multi-tiered forensic analysis scans for passports (MRZ fields), visual centroids, and US Driver's Licenses (**PDF417 barcodes**) to block tool abuse on government identity assets.

---

## 📁 Repository Structure

The repository has been structured to cleanly separate production source code from the validation/test databases to facilitate integration:

```text
├── aegis_kernel/            # Rust DSP Core Kernel source code
├── src/                     # Python command-line entrypoints & forensic pipelines
│   ├── aegis_core/          # Core modules (analyzer.py, cloaking.py)
│   └── cli.py               # Main CLI orchestrator
├── testing/                 # Consolidation of all test-based frameworks
│   ├── test_scripts/        # 14 isolated validation suites
│   ├── logs/                # Audit results & code coverage JSON outputs
│   ├── aegis_testing_temp/  # Raw test dataset assets
│   ├── run_audit.py         # Complete system validator & compiler
│   └── audit_report_production.md  # Final system QA report
├── install_libraries.py     # Hardware-aware deep learning installer
├── requirements.txt         # Production package dependencies
├── REPORT.md                # Technical Report
├── README.md                # README file
├── LICENSE                  # License file
├── SECURITY.md              # Security Policy
├── USAGE_WARNING.md         # Usage Warning
├── ETHICS.md                # Ethics & Compliance
└── HOW_TO_USE.md            # How to Use Guide
```

---

## 💻 System Requirements

Because AEGIS utilizes PyTorch for adversarial face cloaking and running visual classifiers, the recommended system configurations are:

* **Operating System**: Linux (tested on Ubuntu, Fedora, Arch), macOS (Intel & Apple Silicon), or Windows 10/11.
* **Python Version**: Python 3.10, 3.11, or 3.12 (highly recommended for stability).
* **Rust Toolchain**: Cargo/Rustc 1.70+ (required to compile the high-performance DSP engine `aegis_kernel`).
* **Hardware Acceleration (Highly Recommended)**:
  * **NVIDIA GPU**: CUDA 11.8+ compatibility (drastically speeds up cloaking operations).
  * **Apple Silicon (M1/M2/M3/M4)**: Native Metal Performance Shaders (MPS) acceleration.
  * **CPU Mode**: Supported, but processing time will be significantly longer.

---

## 📦 Installation Guide

### Prerequisites
* Python 3.10+ (Try to use Python 3.10, 3.11 & 3.12 as they are most stable in these versions)
* Rust toolchain (`cargo`, `rustc`)

### 1. Setup Virtual Environment
```bash
git clone https://github.com/MSpider3/AEGIS.git
cd AEGIS
python3 -m venv venv
# Windows
source venv/Scripts/activate
# Linux/macOS
source venv/bin/activate
```

### 2. Run the Smart Installer
AEGIS detects your hardware (NVIDIA CUDA, Apple Silicon Metal, or CPU) to configure the optimal PyTorch stack:
```bash
venv/bin/python install_libraries.py
```

### 3. Compile the Rust DSP Kernel
Install Maturin and compile the high-performance bindings:
```bash
VIRTUAL_ENV=venv venv/bin/pip install maturin
VIRTUAL_ENV=venv venv/bin/maturin develop --manifest-path aegis_kernel/Cargo.toml --features python
```

---

## 🛡️ Commands & Usage Examples

Run all commands within the activated virtual environment. Use `PYTHONPATH=src venv/bin/python src/cli.py --help` for full flags.

### 1. Generating a Keypair (`keygen`)
Generate an Ed25519 PEM private/public keypair:
```bash
PYTHONPATH=src venv/bin/python src/cli.py keygen -o keys/
```
* Generates `keys/aegis_private.pem` (private signing key) and `keys/aegis_public.pem` (public verification key).

### 2. Protecting an Image (`protect`)
Apply protection modes. Always output to `.png` to avoid compression degradation:
```bash
PYTHONPATH=src venv/bin/python src/cli.py protect \
  -i input.jpg \
  -o protected.png \
  -m hybrid \
  -k keys/aegis_private.pem \
  -w '{"author": "Jane Doe", "license": "CC-BY-NC"}' \
  --watermark-engine qim-frequency \
  --block-size 16 \
  --robustness-level aggressive \
  --accept-ethics
```
* **Modes (`-m`)**: `hybrid` (cloaking + watermark + noise), `face` (cloaking only), `art` (noise only).
* **Watermark Options**:
  * `--watermark-engine`: Engine type (`legacy` or `qim-frequency`, default: `qim-frequency`).
  * `--block-size`: Shuffling grid block size (`8`, `16`, `32`, `64`, default: `8`).
  * `--robustness-level`: Dynamic delta scaling profile (`standard` or `aggressive`, default: `standard`).

### 3. Verifying and Detecting Copy-Attacks (`verify`)
Extract watermark ownership and verify perceptual bindings:
```bash
PYTHONPATH=src venv/bin/python src/cli.py verify \
  -i protected.png \
  -k keys/aegis_public.pem \
  --watermark-engine qim-frequency \
  --block-size 16 \
  --robustness-level aggressive
```

---

## 🧪 Quality Assurance & Security Validation

A suite of 14 validation files checks for crash recovery, fuzzing, dataset poisoning, and performance:

```bash
# Run the complete test suite and generate the validation report
PYTHONPATH=src venv/bin/python testing/run_audit.py
```
Upon successful completion, the test suite generates an executive audit summary containing detailed metrics under `testing/audit_report_production.md`.

---

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'aegis_kernel'"
* **Fix**: Ensure your virtual environment is active and run the following command:
  ```bash
  VIRTUAL_ENV=venv venv/bin/maturin develop --manifest-path aegis_kernel/Cargo.toml --features python
  ```  

### "Error: Rust toolchain not found"
* **Fix**: Ensure Rust is installed on your system. Refer to the [Rust Installation Guide](https://www.rust-lang.org/tools/install) for instructions.

### "Error: No such file or directory: 'keys/aegis_private.pem'"
* **Fix**: Generate a keypair using the `keygen` command:
  ```bash
  PYTHONPATH=src venv/bin/python src/cli.py keygen -o keys/
  ```

### "TypeError: can only concatenate str (not "NoneType") to str"
* **Fix**: Run the `install_libraries.py` script to ensure all required libraries are installed:
  ```bash
  venv/bin/python install_libraries.py
  ```  

### "Error: No such file or directory: 'protected.png'"
* **Fix**: Ensure that you are running the command from the root directory of the AEGIS repository:
  ```bash
  cd AEGIS
  PYTHONPATH=src venv/bin/python src/cli.py verify \
    -i protected.png \
    -k keys/aegis_public.pem
  ```  

### "Error: ID-Guard activated: Passport detected!" when running protect command
* **Fix**: Use the `--accept-ethics` flag to explicitly consent to the terms of service. This bypasses the ID-Guard check for testing purposes:
  ```bash
  PYTHONPATH=src venv/bin/python src/cli.py protect \
    -i input.jpg \
    -o protected.png \
    -m hybrid \
    -k keys/aegis_private.pem \
    -w '{"author": "Jane Doe", "license": "CC-BY-NC"}' \
    --accept-ethics
  ```  

## ⚖️ Ethics & Compliance

AEGIS is built to protect personal privacy and individual content rights. To prevent misuse, the engine contains **ID-Guard**, an automated compliance checking system that flags and blocks processing of government identification documents (such as passports and driver's licenses).

Before using AEGIS, please review our full guidelines in **[ETHICS.md](ETHICS.md)**.

---

## 🔒 Security Policy & Threat Model

AEGIS uses **Ed25519 asymmetric cryptography** to sign watermarks and **ChaCha8 stream encryption** to secure payload metadata. Structural image binding (aHash) is used to detect copy-and-paste forgery/replay attacks.

For security reports, vulnerability disclosure procedures, and key security practices, please read **[SECURITY.md](SECURITY.md)** and **[Usage Warnings & Best Practices (USAGE_WARNINGS.md)](USAGE_WARNINGS.md)**.

---

## 🤝 Contributing

We welcome contributions from developers, security researchers, and artists! To contribute:
1. Check the [Troubleshooting](#-troubleshooting) section for common issues.
2. Fork the repository and create your feature branch.
3. Run the validation suite (`python testing/run_audit.py`) to verify all checks pass.
4. Open a Pull Request with a clear description of your changes.

---

## 📄 License & Trademarks

### License
This project is open-source and licensed under the **[GNU General Public License v3.0 (GPLv3)](LICENSE)**.

### Trademark Policy
The name **AEGIS**, its logos, branding, and assets are protected trade names and trademarks of this project. 
* While you are free to fork the codebase, modify it, and distribute it under the terms of the GPLv3, you **cannot** use the name "AEGIS" or the official project logos for any commercial forks, redistributed versions, or hosted services without explicit prior written permission.
* Any redistributed version or commercial fork must be renamed to a distinct, non-confusing name, and all references/logos associated with "AEGIS" as a brand must be removed.

---

## 👥 Support & Feedback

For reporting issues, suggestions, or feature requests, please open an issue on the GitHub repository.