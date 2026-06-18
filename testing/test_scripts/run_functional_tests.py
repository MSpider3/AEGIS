import os
import sys
import json
import pytest
import io
import contextlib
from unittest import mock
from PIL import Image
from cli import main
from aegis_core.analyzer import ImageAnalyzer

# Test paths
BASE_TEMP = "testing"
TEST_IMG = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "generated_images", "medium_256.png"))
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "transformed_images"))
MANIFEST_JSON = os.path.join(BASE_TEMP, "manifest.json")

def run_cli_in_process(args_list):
    """Executes the CLI main function in-process with mocked arguments and captures stdout/stderr."""
    old_argv = sys.argv
    sys.argv = ["cli.py"] + args_list
    stdout = io.StringIO()
    stderr = io.StringIO()
    returncode = 0
    try:
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            main()
    except SystemExit as e:
        returncode = e.code if e.code is not None else 0
    except Exception as e:
        stderr.write(str(e))
        returncode = -1
    finally:
        sys.argv = old_argv
    return returncode, stdout.getvalue(), stderr.getvalue()

def test_cli_help():
    """Verify help runs and prints usage instructions."""
    rc, stdout, stderr = run_cli_in_process(["--help"])
    assert rc == 0
    assert "protect" in stdout
    assert "verify" in stdout
    assert "audit" in stdout

def test_cli_no_command():
    """Verify CLI prints help when no subcommand is specified."""
    rc, stdout, stderr = run_cli_in_process([])
    assert rc == 0
    assert "Available actions" in stdout

def test_protect_missing_ethics():
    """Verify protect fails when --accept-ethics is missing."""
    out_png = os.path.join(OUTPUT_DIR, "test_no_ethics.png")
    rc, stdout, stderr = run_cli_in_process([
        "protect", "-i", TEST_IMG, "-o", out_png, "-m", "art"
    ])
    assert rc != 0
    assert "ethics" in stdout or "ethics" in stderr or "ERROR:" in stdout or "ERROR:" in stderr

def test_protect_missing_ethics_json():
    """Verify protect fails when --accept-ethics is missing and --json is set."""
    out_png = os.path.join(OUTPUT_DIR, "test_no_ethics_json.png")
    rc, stdout, stderr = run_cli_in_process([
        "protect", "-i", TEST_IMG, "-o", out_png, "-m", "art", "--json"
    ])
    assert rc != 0
    data = json.loads(stdout)
    assert "error" in data
    assert "ethics" in data["error"]

def test_protect_art_mode():
    """Verify art mode embedding and verification works."""
    out_png = os.path.join(OUTPUT_DIR, "test_art.png")
    if os.path.exists(out_png):
        os.remove(out_png)
        
    payload = '{"author": "Jane", "id": 123}'
    rc, stdout, stderr = run_cli_in_process([
        "protect", "-i", TEST_IMG, "-o", out_png,
        "-m", "art", "-k", "5555", "-w", payload,
        "--accept-ethics"
    ])
    
    assert rc == 0
    assert os.path.exists(out_png)
    
    # Now verify
    rc_v, stdout_v, stderr_v = run_cli_in_process([
        "verify", "-i", out_png, "-k", "5555"
    ])
    
    assert rc_v == 0
    assert "WATERMARK DETECTED SUCCESSFULLY!" in stdout_v
    assert "Jane" in stdout_v

def test_protect_face_mode():
    """Verify face mode (adversarial cloaking only) does not embed watermark."""
    out_png = os.path.join(OUTPUT_DIR, "test_face.png")
    if os.path.exists(out_png):
        os.remove(out_png)
        
    rc, stdout, stderr = run_cli_in_process([
        "protect", "-i", TEST_IMG, "-o", out_png,
        "-m", "face", "--steps", "5", "--accept-ethics"
    ])
    
    assert rc == 0
    assert os.path.exists(out_png)
    
    # Verify should fail because no watermark was embedded
    rc_v, stdout_v, stderr_v = run_cli_in_process([
        "verify", "-i", out_png, "-k", "1337"
    ])
    assert rc_v != 0
    assert "No valid watermark detected" in stdout_v or "FAILED" in stdout_v

def test_protect_hybrid_mode():
    """Verify hybrid mode applies both face cloaking and watermark."""
    out_png = os.path.join(OUTPUT_DIR, "test_hybrid.png")
    if os.path.exists(out_png):
        os.remove(out_png)
        
    rc, stdout, stderr = run_cli_in_process([
        "protect", "-i", TEST_IMG, "-o", out_png,
        "-m", "hybrid", "-k", "9999", "-w", '{"hybrid": true}',
        "--steps", "5", "--accept-ethics"
    ])
    
    assert rc == 0
    assert os.path.exists(out_png)
    
    # Verify
    rc_v, stdout_v, stderr_v = run_cli_in_process([
        "verify", "-i", out_png, "-k", "9999"
    ])
    assert rc_v == 0
    assert "WATERMARK DETECTED SUCCESSFULLY!" in stdout_v

def test_enforced_png_rename():
    """Verify CLI warns and renames to .png if output is set to .jpg."""
    out_jpg = os.path.join(OUTPUT_DIR, "test_rename.jpg")
    expected_png = os.path.join(OUTPUT_DIR, "test_rename.png")
    if os.path.exists(expected_png):
        os.remove(expected_png)
        
    rc, stdout, stderr = run_cli_in_process([
        "protect", "-i", TEST_IMG, "-o", out_jpg,
        "-m", "art", "--accept-ethics"
    ])
    
    assert rc == 0
    assert os.path.exists(expected_png)
    assert not os.path.exists(out_jpg)
    os.remove(expected_png)

def test_verify_wrong_key():
    """Verify extraction fails with wrong key."""
    out_png = os.path.join(OUTPUT_DIR, "test_wrong_key.png")
    if os.path.exists(out_png):
        os.remove(out_png)
        
    rc, stdout, stderr = run_cli_in_process([
        "protect", "-i", TEST_IMG, "-o", out_png,
        "-m", "art", "-k", "1234", "-w", '{"test": 1}',
        "--accept-ethics"
    ])
    assert rc == 0
    
    # Verify with wrong key
    rc_v, stdout_v, stderr_v = run_cli_in_process([
        "verify", "-i", out_png, "-k", "4321"
    ])
    assert rc_v != 0
    assert "No valid watermark detected" in stdout_v or "failed" in stdout_v or "FAILED" in stdout_v

def test_audit_log():
    """Verify audit command reads the log file."""
    rc, stdout, stderr = run_cli_in_process(["audit", "--lines", "5"])
    assert rc == 0
    assert "Retrieving recent audit logs" in stdout

def test_audit_log_missing():
    """Verify audit command handles missing log file gracefully."""
    with mock.patch("os.path.exists", return_value=False):
        rc, stdout, stderr = run_cli_in_process(["audit", "--lines", "5"])
        assert rc == 0
        assert "No audit log file found" in stdout

def test_audit_log_exception():
    """Verify audit command handles log reading exceptions gracefully."""
    # We force an exception when opening aegis_audit.log
    # Let's mock builtins.open
    original_open = open
    def mock_open(file, *args, **kwargs):
        if "aegis_audit.log" in str(file):
            raise IOError("Mocked IO Error")
        return original_open(file, *args, **kwargs)
        
    with mock.patch("builtins.open", side_effect=mock_open):
        rc, stdout, stderr = run_cli_in_process(["audit", "--lines", "5"])
        assert rc != 0
        assert "Failed to read audit log" in stdout

def test_check_aegis_kernel_missing():
    """Verify check_aegis_kernel prints error and exits if kernel is missing."""
    with mock.patch("cli.aegis_kernel", None):
        rc, stdout, stderr = run_cli_in_process(["verify", "-i", TEST_IMG, "-k", "1234"])
        assert rc == 1
        assert "aegis_kernel') is not installed" in stdout

def test_id_guard_override_prompt_abort():
    """Verify that user prompt aborts protection if 'no' is selected."""
    # We need an image that will trigger ID Guard warning
    # We can mock ImageAnalyzer.check_id_guard to return True, 0.99, "Mocked Passport"
    with mock.patch("aegis_core.analyzer.ImageAnalyzer.check_id_guard", return_value=(True, 0.99, "Mocked Passport")):
        with mock.patch("builtins.input", return_value="no"):
            rc, stdout, stderr = run_cli_in_process([
                "protect", "-i", TEST_IMG, "-o", os.path.join(OUTPUT_DIR, "test_abort.png"),
                "-m", "art", "--accept-ethics"
            ])
            assert rc == 0
            assert "Operation aborted by user" in stdout

def test_id_guard_override_prompt_proceed():
    """Verify that user prompt proceeds if 'yes' is selected."""
    out_png = os.path.join(OUTPUT_DIR, "test_proceed.png")
    if os.path.exists(out_png):
        os.remove(out_png)
    with mock.patch("aegis_core.analyzer.ImageAnalyzer.check_id_guard", return_value=(True, 0.99, "Mocked Passport")):
        with mock.patch("builtins.input", return_value="yes"):
            rc, stdout, stderr = run_cli_in_process([
                "protect", "-i", TEST_IMG, "-o", out_png,
                "-m", "art", "--accept-ethics"
            ])
            assert rc == 0
            assert os.path.exists(out_png)
            os.remove(out_png)

def test_id_guard_json_no_override():
    """Verify ID-Guard under JSON format aborts without override warning."""
    with mock.patch("aegis_core.analyzer.ImageAnalyzer.check_id_guard", return_value=(True, 0.99, "Mocked Passport")):
        rc, stdout, stderr = run_cli_in_process([
            "protect", "-i", TEST_IMG, "-o", os.path.join(OUTPUT_DIR, "test_json_abort.png"),
            "-m", "art", "--accept-ethics", "--json"
        ])
        assert rc == 0
        data = json.loads(stdout)
        assert data["flagged"] is True
        assert "reason" in data

def test_verify_file_not_found():
    """Verify verify command handles missing input file."""
    rc, stdout, stderr = run_cli_in_process(["verify", "-i", "nonexistent.png", "-k", "1234"])
    assert rc == 1
    assert "Input file not found" in stdout

def test_verify_invalid_payload_json():
    """Verify error handling when watermark detected payload is not valid JSON."""
    out_png = os.path.join(OUTPUT_DIR, "test_invalid_json.png")
    # Save a valid image first
    img = Image.open(TEST_IMG)
    img.save(out_png)
    
    with mock.patch("aegis_kernel.detect_watermark_py", return_value="not a json"):
        rc, stdout, stderr = run_cli_in_process(["verify", "-i", out_png, "-k", "1234"])
        assert rc == 1
        assert "Watermark verification failed" in stdout
    os.remove(out_png)

def test_verify_signature_mismatch():
    """Verify error handling when watermark signature does not match key."""
    out_png = os.path.join(OUTPUT_DIR, "test_sig_mismatch.png")
    img = Image.open(TEST_IMG)
    img.save(out_png)
    
    # Return valid JSON but with mismatched signature
    bad_sig_json = json.dumps({"payload": "test", "signature": "badsignature"})
    with mock.patch("aegis_kernel.detect_watermark_py", return_value=bad_sig_json):
        rc, stdout, stderr = run_cli_in_process(["verify", "-i", out_png, "-k", "1234"])
        assert rc == 1
        assert "signature verification failed" in stdout
    os.remove(out_png)

def test_verify_generic_exception():
    """Verify error handling when verify hits a generic unexpected exception."""
    out_png = os.path.join(OUTPUT_DIR, "test_generic_err.png")
    img = Image.open(TEST_IMG)
    img.save(out_png)
    
    with mock.patch("aegis_kernel.detect_watermark_py", side_effect=RuntimeError("Generic Rust Error")):
        rc, stdout, stderr = run_cli_in_process(["verify", "-i", out_png, "-k", "1234"])
        assert rc == 1
        assert "Verification failed:" in stdout
    os.remove(out_png)

def test_id_guard_checks():
    """Directly test ImageAnalyzer.check_id_guard on clean assets and government ID assets."""
    analyzer = ImageAnalyzer()
    
    # Clean image check
    is_flagged, conf, reason = analyzer.check_id_guard(TEST_IMG)
    assert not is_flagged
    assert reason == "Clean"
    
    # Find a government ID variant in manifest.json if present
    if os.path.exists(MANIFEST_JSON):
        with open(MANIFEST_JSON, "r", encoding="utf-8") as f:
            records = json.load(f)
        
        id_record = None
        for r in records:
            if "Government IDs" in r["category"] and os.path.exists(r["path"]):
                id_record = r
                break
                
        if id_record:
            # Check ID detection
            is_flagged_id, conf_id, reason_id = analyzer.check_id_guard(id_record["path"])
            assert is_flagged_id
            assert "Passport" in reason_id or "keyword" in reason_id or "Centroid" in reason_id or "C2PA" in reason_id
            
            # Test CLI handling of ID warning overrides
            out_png = os.path.join(OUTPUT_DIR, "test_id_protect.png")
            rc, stdout, stderr = run_cli_in_process([
                "protect", "-i", id_record["path"], "-o", out_png,
                "-m", "art", "--accept-ethics", "--override-warning", "--json"
            ])
            # Should output raw JSON with flagged state
            assert rc == 0
            res_json = json.loads(stdout)
            assert res_json["flagged"] is True
            assert "reason" in res_json

def test_analyzer_ocr_exception():
    """Verify that OCR exceptions do not crash check_id_guard, and are logged."""
    analyzer = ImageAnalyzer()
    with mock.patch("pytesseract.image_to_string", side_effect=Exception("OCR crash")):
        # Should not raise exception
        is_flagged, conf, reason = analyzer.check_id_guard(TEST_IMG)
        assert not is_flagged

def test_analyzer_c2pa_detected():
    """Verify that a valid C2PA manifest with OpenAI/Microsoft vendor flags the image."""
    analyzer = ImageAnalyzer()
    # Mock Reader to yield a reader context manager returning OpenAI vendor manifest JSON
    mock_reader = mock.MagicMock()
    mock_reader.__enter__.return_value = mock_reader
    mock_reader.json.return_value = json.dumps({
        "active_manifest": "manifest1",
        "manifests": {
            "manifest1": {
                "vendor": "OpenAI",
                "assertions": []
            }
        }
    })
    with mock.patch("aegis_core.analyzer.Reader", return_value=mock_reader):
        is_flagged, conf, reason = analyzer.check_id_guard(TEST_IMG)
        assert is_flagged
        assert "C2PA" in reason
        assert conf == 1.0

def test_analyzer_c2pa_exception():
    """Verify that C2PA exceptions do not crash check_id_guard."""
    analyzer = ImageAnalyzer()
    with mock.patch("aegis_core.analyzer.Reader", side_effect=RuntimeError("C2PA library crash")):
        is_flagged, conf, reason = analyzer.check_id_guard(TEST_IMG)
        assert not is_flagged

def test_analyzer_sd_watermark_detected():
    """Verify that detecting a Stable Diffusion watermark flags the image."""
    analyzer = ImageAnalyzer()
    mock_decoder = mock.MagicMock()
    mock_decoder.decode.return_value = b"StableDiffusionV1"
    with mock.patch("aegis_core.analyzer.WatermarkDecoder", return_value=mock_decoder):
        with mock.patch("cv2.imread", return_value=mock.MagicMock()):
            is_flagged, conf, reason = analyzer.check_id_guard(TEST_IMG)
            assert is_flagged
            assert "Stable Diffusion" in reason
            assert conf == 1.0

def test_analyzer_sd_watermark_exception():
    """Verify that Stable Diffusion watermark exceptions do not crash check_id_guard."""
    analyzer = ImageAnalyzer()
    with mock.patch("aegis_core.analyzer.WatermarkDecoder", side_effect=RuntimeError("SD decoder crash")):
        is_flagged, conf, reason = analyzer.check_id_guard(TEST_IMG)
        assert not is_flagged

def test_analyzer_clip_exception():
    """Verify that CLIP exceptions do not crash check_id_guard."""
    analyzer = ImageAnalyzer()
    # Force _init_models to succeed but torch/model run to fail
    analyzer._init_models()
    with mock.patch.object(analyzer, "clip_model", side_effect=RuntimeError("PyTorch CLIP run crash")):
        is_flagged, conf, reason = analyzer.check_id_guard(TEST_IMG)
        assert not is_flagged

def test_analyzer_heuristics_filename():
    """Verify that Midjourney/DALL-E filenames trigger heuristics check."""
    analyzer = ImageAnalyzer()
    dummy_file = "dalle_generated_art_123.png"
    with open(dummy_file, "w") as f:
        f.write("")
    try:
        is_flagged, conf, reason = analyzer.check_id_guard(dummy_file)
        assert is_flagged
        assert "heuristics" in reason
        assert conf == 0.70
    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)

def test_analyzer_missing_imports():
    import sys
    import importlib
    
    # Save original __import__
    real_import = __import__
    
    def mock_import(name, *args, **kwargs):
        if name in ["c2pa", "passporteye", "pytesseract", "open_clip", "imwatermark"]:
            raise ImportError(f"Mocked import error for {name}")
        return real_import(name, *args, **kwargs)
        
    # Remove from sys.modules to force reload
    if 'aegis_core.analyzer' in sys.modules:
        del sys.modules['aegis_core.analyzer']
        
    with mock.patch("builtins.__import__", side_effect=mock_import):
        import aegis_core.analyzer
        assert aegis_core.analyzer.Reader is None
        assert aegis_core.analyzer.read_mrz is None
        assert aegis_core.analyzer.pytesseract is None
        assert aegis_core.analyzer.open_clip is None
        assert aegis_core.analyzer.WatermarkDecoder is None
        
    # Reload with real imports to restore state
    if 'aegis_core.analyzer' in sys.modules:
        del sys.modules['aegis_core.analyzer']
    import aegis_core.analyzer


def test_cloaker_offline_mode():
    from aegis_core.cloaking import PgdCloaker
    with mock.patch("aegis_core.cloaking.models.resnet18", side_effect=OSError("offline error")):
        with pytest.raises(RuntimeError) as exc_info:
            PgdCloaker(surrogate_name="resnet18", offline=True)
        assert "not cached locally" in str(exc_info.value)


def test_cloaker_invalid_surrogate():
    from aegis_core.cloaking import PgdCloaker
    with mock.patch("aegis_core.cloaking.models.mobilenet_v2") as mock_mbv2:
        PgdCloaker(surrogate_name="invalid_surrogate")
        mock_mbv2.assert_called_once()


def test_cloaker_valid_surrogates():
    from aegis_core.cloaking import PgdCloaker
    with mock.patch("aegis_core.cloaking.models.resnet18") as mock_resnet18:
        PgdCloaker(surrogate_name="resnet18")
        mock_resnet18.assert_called_once()
        
    with mock.patch("aegis_core.cloaking.models.mobilenet_v3_large") as mock_mbv3:
        PgdCloaker(surrogate_name="mobilenet_v3_large")
        mock_mbv3.assert_called_once()


def test_analyzer_no_clip_env():
    import os
    from aegis_core.analyzer import ImageAnalyzer
    with mock.patch.dict(os.environ, {"AEGIS_NO_CLIP": "1"}):
        analyzer = ImageAnalyzer()
        analyzer._init_models()
        assert analyzer.clip_model is None


def test_analyzer_failed_clip_load():
    from aegis_core.analyzer import ImageAnalyzer
    with mock.patch("open_clip.create_model_and_transforms", side_effect=Exception("Failed to load CLIP")):
        analyzer = ImageAnalyzer()
        analyzer._init_models()
        assert analyzer.clip_model is None


def test_analyzer_missing_id_keywords():
    from aegis_core.analyzer import ImageAnalyzer
    with mock.patch("os.path.exists", return_value=False):
        analyzer = ImageAnalyzer()
        assert "passport" in analyzer.id_keywords


def test_analyzer_check_id_guard_nonexistent():
    from aegis_core.analyzer import ImageAnalyzer
    analyzer = ImageAnalyzer()
    is_flagged, conf, reason = analyzer.check_id_guard("nonexistent.png")
    assert not is_flagged
    assert "not found" in reason.lower()


def test_analyzer_mrz_detected():
    from aegis_core.analyzer import ImageAnalyzer
    analyzer = ImageAnalyzer()
    
    mock_mrz_obj = mock.MagicMock()
    mock_mrz_obj.to_dict.return_value = {"valid_score": 95}
    
    with mock.patch("aegis_core.analyzer.read_mrz", return_value=mock_mrz_obj):
        is_flagged, conf, reason = analyzer.check_id_guard(TEST_IMG)
        assert is_flagged
        assert "MRZ" in reason or "Passport" in reason
        assert conf == 0.99


def test_analyzer_ocr_keyword_detected():
    from aegis_core.analyzer import ImageAnalyzer
    analyzer = ImageAnalyzer()
    
    with mock.patch("pytesseract.image_to_string", return_value="This is a Passport document"):
        is_flagged, conf, reason = analyzer.check_id_guard(TEST_IMG)
        assert is_flagged
        assert "keyword" in reason.lower()
        assert conf == 0.95


def test_analyzer_clip_centroid_id_match():
    from aegis_core.analyzer import ImageAnalyzer
    analyzer = ImageAnalyzer()
    
    # Prevent _init_models from overwriting our mocks
    analyzer._init_models = mock.MagicMock()
    
    # Mock clip model and centroids directly
    import torch
    
    analyzer.clip_model = mock.MagicMock()
    analyzer.clip_model.return_value = torch.tensor([[1.0]])
    analyzer.c_id = torch.tensor([[0.9]])
    analyzer.c_non_id = torch.tensor([[0.1]])
    analyzer.clip_preprocess = mock.MagicMock()
    analyzer.device = torch.device("cpu")
    
    is_flagged, conf, reason = analyzer.check_id_guard(TEST_IMG)
    assert is_flagged
    assert "centroid" in reason.lower()
    # score = sim_id / (sim_id + sim_non_id) = 0.9 / (0.9 + 0.1) = 0.9
    assert abs(conf - 0.9) < 1e-5


def test_protect_clean_json():
    import json
    out_png = os.path.join(OUTPUT_DIR, "test_clean_json.png")
    if os.path.exists(out_png):
        os.remove(out_png)
    rc, stdout, stderr = run_cli_in_process([
        "protect", "-i", TEST_IMG, "-o", out_png,
        "-m", "art", "--accept-ethics", "--json"
    ])
    assert rc == 0
    data = json.loads(stdout)
    assert data["flagged"] is False
    assert data["reason"] == "Clean"
    if os.path.exists(out_png):
        os.remove(out_png)


def test_protect_hybrid_no_payload():
    out_png = os.path.join(OUTPUT_DIR, "test_hybrid_no_payload.png")
    if os.path.exists(out_png):
        os.remove(out_png)
    rc, stdout, stderr = run_cli_in_process([
        "protect", "-i", TEST_IMG, "-o", out_png,
        "-m", "hybrid", "--steps", "2", "--accept-ethics"
    ])
    assert rc == 0
    assert os.path.exists(out_png)
    
    rc_v, stdout_v, stderr_v = run_cli_in_process([
        "verify", "-i", out_png, "-k", "1337"
    ])
    assert rc_v == 0
    assert "AEGIS Image Shield" in stdout_v
    if os.path.exists(out_png):
        os.remove(out_png)


def test_protect_hybrid_watermark_failure_cleanup():
    out_png = os.path.join(OUTPUT_DIR, "test_hybrid_fail_cleanup.png")
    with mock.patch("aegis_kernel.embed_watermark_py", side_effect=ValueError("Mocked embedding failure")):
        rc, stdout, stderr = run_cli_in_process([
            "protect", "-i", TEST_IMG, "-o", out_png,
            "-m", "hybrid", "--steps", "2", "--accept-ethics"
        ])
        assert rc == 1
        assert "Watermark embedding failed" in stdout


def test_verify_missing_signature_keys():
    import json
    out_png = os.path.join(OUTPUT_DIR, "test_verify_missing_keys.png")
    img = Image.open(TEST_IMG)
    img.save(out_png)
    bad_json = json.dumps({"foo": "bar"})
    with mock.patch("aegis_kernel.detect_watermark_py", return_value=bad_json):
        rc, stdout, stderr = run_cli_in_process(["verify", "-i", out_png, "-k", "1234"])
        assert rc == 1
        assert "Watermark signature format invalid or missing" in stdout
    if os.path.exists(out_png):
        os.remove(out_png)


def test_cli_main_block():
    import runpy
    import sys
    import contextlib
    import io
    old_argv = sys.argv
    sys.argv = ["cli.py", "--help"]
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            runpy.run_path("src/cli.py", run_name="__main__")
    except SystemExit as e:
        assert e.code == 0
    finally:
        sys.argv = old_argv


def test_cli_keygen_and_file_key_seed():
    import shutil
    from cli import parse_seed, load_or_derive_private_key, load_or_derive_public_key
    from cryptography.hazmat.primitives import serialization
    
    temp_keys_dir = "temp_keys_test"
    if os.path.exists(temp_keys_dir):
        shutil.rmtree(temp_keys_dir)
        
    rc, stdout, stderr = run_cli_in_process(["keygen", "--out-dir", temp_keys_dir])
    assert rc == 0
    assert "Private Key" in stdout
    
    priv_path = os.path.join(temp_keys_dir, "aegis_private.pem")
    pub_path = os.path.join(temp_keys_dir, "aegis_public.pem")
    assert os.path.exists(priv_path)
    assert os.path.exists(pub_path)
    
    # Test parse_seed on public key path
    seed1 = parse_seed(pub_path)
    assert isinstance(seed1, int)
    
    # Test parse_seed on private key path
    seed2 = parse_seed(priv_path)
    assert isinstance(seed2, int)
    
    # Test load private key
    priv_key = load_or_derive_private_key(priv_path)
    assert priv_key is not None
    
    # Test load public key
    pub_key = load_or_derive_public_key(pub_path)
    assert pub_key is not None
    
    # Test load public key from private key file path (triggers priv.public_key())
    pub_from_priv = load_or_derive_public_key(priv_path)
    assert pub_from_priv is not None
    
    # Test load public key from random file (triggers exception fallback)
    bad_key_file = os.path.join(temp_keys_dir, "bad_key.pem")
    with open(bad_key_file, "w") as f:
        f.write("arbitrary_garbage")
    
    pub_fallback = load_or_derive_public_key(bad_key_file)
    assert pub_fallback is not None
    
    priv_fallback = load_or_derive_private_key(bad_key_file)
    assert priv_fallback is not None

    if os.path.exists(temp_keys_dir):
        shutil.rmtree(temp_keys_dir)


def test_cli_audit_command():
    from cli import AUDIT_LOG_PATH
    # Test basic audit command
    rc, stdout, stderr = run_cli_in_process(["audit", "--lines", "2"])
    assert rc == 0
    
    # Test audit command when log is missing
    real_exists = os.path.exists
    def mock_exists(p):
        if p == AUDIT_LOG_PATH:
            return False
        return real_exists(p)
        
    with mock.patch("os.path.exists", side_effect=mock_exists):
        rc_missing, stdout_missing, stderr_missing = run_cli_in_process(["audit"])
        assert rc_missing == 0
        assert "No audit log file" in stdout_missing

    # Test audit command when file read fails
    def mock_open(*args, **kwargs):
        raise IOError("Mocked read failure")
    with mock.patch("builtins.open", side_effect=mock_open):
        rc_err, stdout_err, stderr_err = run_cli_in_process(["audit"])
        assert rc_err == 1
        assert "Failed to read audit log" in stdout_err


def test_cli_verify_corrupted_or_missing_image():
    # 1. Nonexistent image protect
    rc, stdout, stderr = run_cli_in_process(["protect", "-i", "nonexistent.png", "-o", "out.png", "--accept-ethics"])
    assert rc == 1
    assert "not found" in stdout
    
    # 2. Nonexistent image protect JSON
    rc, stdout, stderr = run_cli_in_process(["protect", "-i", "nonexistent.png", "-o", "out.png", "--accept-ethics", "--json"])
    assert rc == 1
    assert "not found" in stdout
    
    # 3. Corrupted image protect
    corrupt_file = os.path.join(OUTPUT_DIR, "corrupt_test.png")
    with open(corrupt_file, "w") as f:
        f.write("corrupt file content")
    try:
        rc, stdout, stderr = run_cli_in_process(["protect", "-i", corrupt_file, "-o", "out.png", "--accept-ethics"])
        assert rc == 1
        assert "not a valid or supported image" in stdout
        
        # 4. Corrupted image protect JSON
        rc, stdout, stderr = run_cli_in_process(["protect", "-i", corrupt_file, "-o", "out.png", "--accept-ethics", "--json"])
        assert rc == 1
        assert "Invalid or corrupted image" in stdout
        
        # 5. Nonexistent image verify
        rc, stdout, stderr = run_cli_in_process(["verify", "-i", "nonexistent.png", "-k", "1234"])
        assert rc == 1
        assert "Input file not found" in stdout
        
        # 6. Corrupted image verify
        rc, stdout, stderr = run_cli_in_process(["verify", "-i", corrupt_file, "-k", "1234"])
        assert rc == 1
        assert "not a valid or supported image" in stdout
    finally:
        if os.path.exists(corrupt_file):
            os.remove(corrupt_file)


def test_analyzer_check_id_guard_bypasses_and_import_errors():
    from aegis_core.analyzer import ImageAnalyzer
    # 1. Bypassed via env
    with mock.patch.dict(os.environ, {"AEGIS_NO_FORENSICS": "1"}):
        analyzer = ImageAnalyzer()
        is_flagged, conf, reason = analyzer.check_id_guard(TEST_IMG)
        assert is_flagged is False
        assert "Bypassed" in reason
        
    # 2. File not found
    analyzer = ImageAnalyzer()
    is_flagged, conf, reason = analyzer.check_id_guard("nonexistent_image.png")
    assert is_flagged is False
    assert "File not found" in reason

    # 3. Simulate missing imports to trigger the ImportError fallbacks
    real_import = __import__
    def mock_import(name, *args, **kwargs):
        if name in ["passporteye", "pdf417decoder", "pytesseract", "c2pa", "imwatermark"]:
            raise ImportError(f"Mocked import error for {name}")
        return real_import(name, *args, **kwargs)
        
    import sys
    if 'aegis_core.analyzer' in sys.modules:
        del sys.modules['aegis_core.analyzer']
        
    with mock.patch("builtins.__import__", side_effect=mock_import):
        import aegis_core.analyzer
        mock_analyzer = aegis_core.analyzer.ImageAnalyzer()
        mock_analyzer.clip_model = None
        mock_analyzer._init_models = mock.MagicMock()
        is_flagged, conf, reason = mock_analyzer.check_id_guard(TEST_IMG)
        assert is_flagged is False
        
    # Reload with real imports
    if 'aegis_core.analyzer' in sys.modules:
        del sys.modules['aegis_core.analyzer']
    import aegis_core.analyzer


def test_analyzer_pdf417_barcode_scan():
    from aegis_core.analyzer import ImageAnalyzer
    analyzer = ImageAnalyzer()
    
    mock_decoder = mock.MagicMock()
    mock_decoder.decode.return_value = 1
    mock_decoder.barcode_data_index_to_string.return_value = "DAQ: DL12345 ID012"
    
    with mock.patch("aegis_core.analyzer.PDF417Decoder", return_value=mock_decoder):
        is_flagged, conf, reason = analyzer.check_id_guard(TEST_IMG)
        assert is_flagged
        assert "PDF417" in reason
        assert conf == 0.98


def test_cloaker_bypasses_and_exception_paths():
    from aegis_core.cloaking import PgdCloaker
    # 1. Bypass via env
    with mock.patch.dict(os.environ, {"AEGIS_NO_CLIP": "1"}):
        cloaker = PgdCloaker()
        assert cloaker.model is None
        res_img = cloaker.cloak_image(TEST_IMG)
        assert res_img is not None
        
    # 2. Load model raises non-offline OSError
    with mock.patch.dict(os.environ, {"TORCH_HUB_OFFLINE": "0"}):
        with mock.patch("torchvision.models.resnet18", side_effect=OSError("Different system OS error")):
            with pytest.raises(OSError) as exc_info:
                PgdCloaker(surrogate_name="resnet18")
            assert "Different system OS error" in str(exc_info.value)


def test_pil_resample_fallback():
    import PIL.Image
    class ImageWrapper:
        def __init__(self, original):
            self._original = original
        def __getattr__(self, name):
            if name == "Resampling":
                raise AttributeError("Mocked Resampling attribute error")
            return getattr(self._original, name)
            
    with mock.patch("cli.Image", ImageWrapper(PIL.Image)):
        out_png = os.path.join(OUTPUT_DIR, "test_resample_fallback.png")
        if os.path.exists(out_png):
            os.remove(out_png)
        rc, stdout, stderr = run_cli_in_process([
            "protect", "-i", TEST_IMG, "-o", out_png,
            "-m", "art", "-w", "test_payload", "--accept-ethics"
        ])
        assert rc == 0, f"stdout: {stdout}\nstderr: {stderr}"
        if os.path.exists(out_png):
            os.remove(out_png)


if __name__ == "__main__":
    pytest.main([__file__])
