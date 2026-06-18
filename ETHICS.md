# AEGIS: Ethics and Acceptable Use Policy

The **AEGIS (Anonymous Encryption & Generative Image Shield)** project was developed with a singular focus: **protecting personal privacy against unauthorized mass surveillance, web scraping, and non-consensual AI model training.** 

By using this software, you agree to adhere strictly to the following ethical guidelines and terms of use.

## 1. Intended Purpose
AEGIS is designed for the protection of personal portraits, private artwork, and creative digital assets. Its primary functions are:
- **Anti-Scraping**: Preventing unauthorized generative AI models from successfully extracting features from your artwork or face.
- **Privacy Preservation**: Making it difficult for mass facial-recognition systems to accurately index your personal photos uploaded to social media.
- **Provenance Tracking**: Enabling creators to assert ownership over their digital art through invisible watermarks.

---

## 2. Strictly Prohibited Uses
This software features adversarial obfuscation capabilities. Under no circumstances may AEGIS be used for:
- **Identity Fraud**: Altering official government documents, passports, driver's licenses, or biometric identity cards.
- **Evading Legal Identification**: Obfuscating imagery used for KYC (Know Your Customer) processes, banking verification, or law enforcement identification.
- **Deepfakes & Disinformation**: Attempting to bypass deepfake detection algorithms or masking the origin of synthetic media intended to deceive the public.
- **Malicious Hiding**: Embedding malicious payloads, CSAM, or illicit material within the invisible watermark channels.

---

## 3. Built-in Compliance (AEGIS-ID-Guard)
To enforce these ethical boundaries, AEGIS includes **ID-Guard**, a multi-tiered compliance checking system:
- **Image Dimension & Structural Checks**: Blocks images matching standard passport or identity document aspect ratios.
- **OCR Passport/Document Scanning**: Scans text segments for passport-related strings, Machine Readable Zones (MRZ), or national identity keywords.
- **Barcode Analysis**: Scans images for **PDF417 stacked linear barcodes**, which are standard on US Driver's Licenses and military IDs.
- **Blocking Action**: If ID-Guard flags the input image, AEGIS immediately blocks the protection process, logs the flagged event, and exits.
- **No Bypass**: Bypassing, disabling, or modifying the ID-Guard compliance system is a strict violation of this Acceptable Use Policy.

---

## 4. Audit Logging
AEGIS maintains a local, offline audit log of all operations performed (both successful protections and blocked attempts). This log is kept strictly on your local machine to preserve your privacy, but it exists to provide an accountable trail of usage.

---

## 5. Disclaimer of Liability
AEGIS is provided as an experimental research tool. The developers assume no liability for the misuse of this software, nor do they guarantee absolute protection against all future AI models or recognition systems. Privacy is an arms race, and users should employ this tool as one part of a broader digital safety strategy.