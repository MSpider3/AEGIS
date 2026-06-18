import os
import json
import logging
from typing import Tuple, Dict, Any

import sys

# Lazy-loaded forensic libraries (loaded on-demand in check_id_guard)
Reader = None
read_mrz = None
pytesseract = None
WatermarkDecoder = None
PDF417Decoder = None
from PIL import Image

# Lazy-loaded ML libraries (loaded on-demand via _init_models)
torch = None
F = None
open_clip = None

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add a file handler specifically to write audit events to aegis_audit.log
try:
    file_handler = logging.FileHandler("aegis_audit.log", mode="a", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
except Exception as e:
    logger.warning(f"Failed to initialize persistent audit log file: {e}")

class ImageAnalyzer:
    def __init__(self):
        self.device = None
        self.id_keywords = self._load_keywords()
        self.clip_model = None
        self.clip_preprocess = None
        self.c_id = None
        self.c_non_id = None

    def _init_models(self):
        if os.environ.get("AEGIS_NO_CLIP") == "1":
            logger.info("CLIP model initialization bypassed via AEGIS_NO_CLIP env var.")
            return
        
        global torch, F, open_clip
        if torch is None or F is None:
            import torch
            import torch.nn.functional as F
        if open_clip is None:
            try:
                import open_clip
            except ImportError:
                open_clip = None

        if self.device is None and torch is not None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")

        if open_clip is not None and self.clip_model is None:
            try:
                logger.info("Lazy-loading open_clip Vision backbone...")
                full_model, _, self.clip_preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='openai')
                
                # Tokenize and encode reference texts for zero-shot ID classification
                texts = open_clip.tokenize([
                    "a photo of a government identity document, passport, driver's license, or identification card",
                    "a portrait, painting, artwork, photograph of a person, landscape, or general image"
                ])
                with torch.no_grad():
                    text_features = full_model.encode_text(texts.to(self.device))
                    text_features = F.normalize(text_features, dim=-1)
                    self.c_id = text_features[0:1]
                    self.c_non_id = text_features[1:2]
                
                self.clip_model = full_model.visual.to(self.device)
                self.clip_model.eval()
                del full_model # Immediately free the text encoder from memory
                
                logger.info("Successfully loaded open_clip Vision backbone and zero-shot ID centroids.")
            except Exception as e:
                logger.warning(f"Failed to load open_clip Vision model: {e}")

    def _load_keywords(self) -> set:
        keywords = set()
        keyword_file = os.path.join(os.path.dirname(__file__), 'id_keywords.txt')
        if os.path.exists(keyword_file):
            with open(keyword_file, 'r', encoding='utf-8') as f:
                for line in f:
                    kw = line.strip().lower()
                    if kw:
                        keywords.add(kw)
        else:
            keywords = {"government", "identity", "driver license", "dob", "passport"}
        return keywords

    def check_id_guard(self, image_path: str) -> Tuple[bool, float, str]:
        """
        Multilayer forensic detection pipeline.
        Tier 1: Physical Compliance (MRZ, OCR)
        Tier 2: Stage 1 Cryptographic Triage (C2PA - OpenAI/Adobe)
        Tier 3: Stage 2 Watermark Triage (Stable Diffusion invisible-watermark)
        Tier 4: Stage 3 Mathematical Fallback (CLIP Visual Centroid Distance)
        """
        if os.environ.get("AEGIS_NO_FORENSICS") == "1":
            return False, 0.0, "Bypassed via AEGIS_NO_FORENSICS"

        if not os.path.exists(image_path):
            return False, 0.0, "File not found"

        # Tier 1a: MRZ Passport Validation
        global read_mrz
        if read_mrz is None:
            try:
                from passporteye import read_mrz
            except ImportError:
                read_mrz = False
        
        if read_mrz:
            try:
                mrz = read_mrz(image_path)
                if mrz is not None:
                    mrz_data = mrz.to_dict()
                    if mrz_data.get('valid_score', 0) > 80:
                        return True, 0.99, "Machine Readable Zone (MRZ) Passport Pattern Detected"
            except Exception as e:
                logger.debug(f"MRZ scan failed: {e}")

        # Tier 1b: PDF417 Barcode validation (for US driver's licenses)
        global PDF417Decoder
        if PDF417Decoder is None:
            try:
                from pdf417decoder import PDF417Decoder
            except ImportError:
                PDF417Decoder = False

        if PDF417Decoder and Image is not None:
            try:
                img = Image.open(image_path)
                decoder = PDF417Decoder(img)
                if decoder.decode() > 0:
                    decoded_str = decoder.barcode_data_index_to_string(0)
                    if decoded_str and ("DL" in decoded_str or "ID" in decoded_str or "DAQ" in decoded_str):
                        return True, 0.98, "PDF417 Driver's License Barcode Detected"
            except Exception as e:
                logger.debug(f"PDF417 barcode scan failed: {e}")

        # Tier 1c: Tesseract OCR text matching
        global pytesseract
        if pytesseract is None:
            try:
                import pytesseract
            except ImportError:
                pytesseract = False
        
        if pytesseract and Image is not None:
            try:
                img = Image.open(image_path)
                try:
                    text = pytesseract.image_to_string(img, lang='eng+spa+fra+deu+hin+ara+chi_sim').lower()
                except Exception:
                    # Fallback to English if multi-lang packs are not installed
                    text = pytesseract.image_to_string(img, lang='eng').lower()
                
                # Define high-confidence keywords
                high_conf = {
                    "passport", "driver license", "driver licence", "identity card", "id card", 
                    "aadhar", "ssn", "social security", "permis de conduire", "führerschein", 
                    "pasaporte", "passeport", "reisepass", "permis de conducir", "cedula", 
                    "national identity", "national id", "licencia de conducir", "licencia de manejo"
                }
                
                # Check for high-confidence keywords
                found_high = [kw for kw in high_conf if kw in text]
                if found_high:
                    return True, 0.95, f"Found high-confidence ID keyword '{found_high[0]}' in OCR scan"
                
                # Fallback to medium confidence
                matches = sum(1 for kw in self.id_keywords if kw in text)
                if matches >= 2:
                    return True, 0.90, f"Found {matches} Government ID matching keywords in physical OCR"
            except Exception as e:
                logger.debug(f"OCR scan failed: {e}")

        # Tier 2: Stage 1 Cryptographic Triage (C2PA)
        global Reader
        if Reader is None:
            try:
                from c2pa import Reader
            except ImportError:
                Reader = False
        
        if Reader:
            try:
                with Reader(image_path) as reader:
                    manifest_data = reader.json()
                    if manifest_data:
                        manifest_dict = json.loads(manifest_data)
                        active_manifest = manifest_dict.get("active_manifest", "")
                        manifests = manifest_dict.get("manifests", {})
                        active_info = manifests.get(active_manifest, {})
                        vendor = active_info.get("vendor", "").lower()
                        assertions = json.dumps(active_info.get("assertions", [])).lower()
                        
                        if "openai" in vendor or "microsoft" in vendor or "openai" in assertions:
                            return True, 1.0, "C2PA Cryptographic Signature Detected (OpenAI/Microsoft)"
            except Exception as e:
                logger.debug(f"C2PA check failed: {e}")

        # Tier 3: Stage 2 Open-Source Watermark Triage (Stable Diffusion)
        global WatermarkDecoder
        if WatermarkDecoder is None:
            try:
                from imwatermark import WatermarkDecoder
            except ImportError:
                WatermarkDecoder = False
        
        if WatermarkDecoder:
            try:
                import cv2
                bgr = cv2.imread(image_path)
                if bgr is not None:
                    decoder = WatermarkDecoder('bytes', 136)
                    watermark = decoder.decode(bgr, 'dwtDct')
                    try:
                        dec_str = watermark.decode('utf-8')
                        if "StableDiffusion" in dec_str:
                            return True, 1.0, "Stable Diffusion Invisible Watermark Detected"
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"SD Watermark check failed: {e}")

        # Tier 4: Stage 3 Mathematical Fallback (CLIP Visual Centroid Distance)
        self._init_models()
        if self.clip_model is not None and Image is not None:
            try:
                img = Image.open(image_path).convert("RGB")
                img_tensor = self.clip_preprocess(img).unsqueeze(0).to(self.device)
                
                with torch.no_grad():
                    v = self.clip_model(img_tensor)
                    v = F.normalize(v, p=2, dim=-1)

                    sim_id = torch.matmul(v, self.c_id.T).item()
                    sim_non_id = torch.matmul(v, self.c_non_id.T).item()
                    
                    if sim_id > sim_non_id: 
                        score = sim_id / (sim_id + sim_non_id)
                        return True, score, f"Visual Centroid Distance flagged as Government ID (Score: {score*100:.1f}%)"
            except Exception as e:
                logger.debug(f"Visual Centroid classification failed: {e}")

        # Tier 5: Heuristics Fallback
        filename = os.path.basename(image_path).lower()
        if "midjourney" in filename or "dalle" in filename or "stable_diffusion" in filename:
            return True, 0.70, "Suspicious generator filename heuristics matched"
            
        return False, 0.0, "Clean"

    def log_operation(self, image_path: str, action: str, details: str):
        logger.info(f"AUDIT LOG | Action: {action} | File: {image_path} | Details: {details}")
