# AEGIS Security & Threat Model

This document outlines the security architecture of AEGIS, known limitations, and how to securely report vulnerabilities.

## 1. Threat Model
AEGIS assumes the following capabilities of an adversary (e.g., an unauthorized web scraper or facial recognition model):
- **Black-box access**: The adversary processes the shielded image without knowing the specific AEGIS parameters (private/public keys, perturbation epsilon) used.
- **Automated transformations**: The adversary may routinely apply resizing, JPEG compression, or center-cropping before feeding images into their models.
- **Model discrepancy**: The adversary's target model architecture is unknown and likely differs from the surrogate models (e.g., MobileNetV2) AEGIS optimizes against.

---

## 2. Cryptographic Security Enhancements
Unlike standard steganographic systems, the AEGIS watermarking engine is built on robust production cryptography:
1. **Asymmetric Verification (Ed25519)**: The watermark payload is cryptographically signed using the owner's private key. The public key is used to verify ownership. This prevents adversaries from forging or spoofing watermarks.
2. **Confidentiality Encryption (ChaCha8)**: The watermark payload and signature are encrypted using a **ChaCha8 stream cipher** derived from the public key, preventing cleartext metadata extraction by third parties.
3. **Copy-Attack Prevention (aHash Perceptual Binding)**: An Average Hash (aHash) of the cover image is computed and cryptographically signed inside the watermark payload. Verifiers automatically compare the computed aHash of the verified image with the signed aHash. Replaying or copying the watermark onto another image will trigger a Hamming distance mismatch ($D_H > 10$ bits), flagging the forgery.
4. **Secure Coordinate Shuffling (ChaCha8Rng)**: Shuffling of the $8 \times 8$ blocks is coordinated using a cryptographically secure `ChaCha8Rng` derived from the public key to prevent block coordinate leakage.

---

## 3. Limitations of Protection
While AEGIS employs state-of-the-art Projected Gradient Descent (PGD) and differentiable augmentations to maximize robustness, users must understand:
1. **Adaptive Attacks**: If an adversary explicitly trains an AI model to recognize and filter out AEGIS noise (adversarial training), the protection may degrade.
2. **Extreme Transformations**: The invisible watermark and adversarial noise will not survive extreme degradation, such as heavy blurring, aggressive downscaling (< 64px), or complete structural alteration (e.g., heavy stylization filters).

---

## 4. ID-Guard Security
The AEGIS-ID-Guard mechanism relies on a local PyTorch transformer model (SMOGY), MRZ passports regex parsing, and PDF417 driver's license barcode scanning. It is designed as an ethical failsafe, not an impenetrable barrier. Malicious users with direct access to the source code can theoretically bypass this check by modifying the Python files. We rely on the honor system and the open-source community to report forks or hosted instances that maliciously disable this safeguard.

---

## 5. Reporting Vulnerabilities
If you discover a vulnerability in AEGIS—such as an exploit that causes the Python CLI to crash, a memory leak in the Rust kernel, or a consistent method to bypass the watermark error correction—we ask that you practice responsible disclosure.

Please do **NOT** open a public issue on GitHub. Instead, report the vulnerability privately to the project maintainers via encrypted email or the repository's private security advisory portal.

---

## 6. Offline Guarantee
AEGIS is designed with a strict "Local-First" security policy. 
- The Python CLI runs entirely offline. Surrogate model weights and ID-Guard transformers are cached locally.
- No network requests are made to external servers to process your images once models are cached.
You can—and are encouraged to—use AEGIS on an air-gapped machine for maximum privacy (using the `--offline` flag).
