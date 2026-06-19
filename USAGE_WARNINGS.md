# AEGIS Usage Warnings and Best Practices

Before relying on AEGIS to protect your personal images or digital artwork, please carefully read and understand the following warnings and best practices.

## 1. Asymmetric Key Security (Ed25519)
AEGIS has transitioned from symmetric keys to a production-grade **Ed25519 asymmetric cryptography** system:
- **Private Key (`aegis_private.pem`)**: Used during the `protect` command to sign the watermark. Keep this file strictly private. If an adversary obtains your private key, they can overwrite or spoof your watermarks.
- **Public Key (`aegis_public.pem`)**: Used during the `verify` command to authenticate the watermark. Anyone can use your public key to verify your ownership without being able to forge it.
- **PIN/Text Passphrase Compatibility**: You can still use standard PINs/text keys (like `1337` or `mysecretpass`) for backward compatibility or quick testing. The CLI will deterministically derive an Ed25519 private key from the string using SHA-256.
- **No Key Recovery**: If you lose both your private key file and passphrase, **your watermark cannot be verified**. Treat your private key file/passphrase with the same security as a password or SSH key.

## 2. Visual Artifacts vs. Protection Strength
AEGIS works by injecting mathematical noise and high-frequency patterns:
- **Higher Strength = Better Protection**: A masking strength of `8.0` or higher provides stronger defense against facial recognition surrogate models and AI scrapers.
- **Higher Strength = More Visible Artifacts**: However, high strength will introduce visible static, grain, or blocky artifacts into your image.
**Best Practice**: Start with the default strength (`5.0`). If the image is highly detailed or noisy, you can increase it. If it is a clean, flat-colored artwork, you may need to decrease it to preserve visual quality.

## 3. Lossless Output Formats
When AEGIS outputs a protected image, it has precisely calculated the pixel values to preserve the adversarial noise and the invisible watermark.
- **Avoid saving the output as heavily compressed JPEGs.** With the introduction of the modern `qim-frequency` engine, AEGIS watermarks are highly robust and can survive lossy JPEG compression down to Quality 75 (Q=75) as well as resizing. However, saving the immediate output as a heavily compressed JPEG (Q < 75) should still be avoided as it can destroy the watermark and weaken the adversarial noise.
- The Python CLI outputs **PNG** files by default to preserve maximum protection integrity.
**Best Practice**: Keep your master protected copies as PNG files. If you must upload to a platform that compresses images (like social media), the PNG format ensures the highest possible starting quality before the platform's compression occurs.

## 4. Copy-Attack Replay Warnings
AEGIS includes built-in Average Hash (aHash) structural fingerprinting.
- If you attempt to verify a watermark that has been copied or replayed onto a different cover image, the `verify` command will display a `POTENTIAL COPY/REPLAY ATTACK DETECTED!` warning, showing that the watermark was not originally embedded in that image.
- Perceptual binding verification succeeds if the Hamming distance between the image fingerprint and the embedded hash is $\le 10$ bits.

## 5. Not a Silver Bullet
**AI models are constantly evolving. An image protected today might become vulnerable to a completely new architecture of AI model developed next year. 
AEGIS significantly raises the cost and difficulty for unauthorized scrapers, but it cannot mathematically guarantee absolute protection against all future technologies. Use AEGIS as one layer in your digital privacy strategy.**
