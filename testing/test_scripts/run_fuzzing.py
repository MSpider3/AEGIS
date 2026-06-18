import os
import subprocess
import random
import string
import json

BASE_TEMP = "testing"
CLI_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src", "cli.py"))
VENV_PYTHON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "venv", "bin", "python"))

def generate_random_string(length):
    return ''.join(random.choice(string.ascii_letters + string.digits + " ") for _ in range(length))

def run_fuzz_case(args):
    try:
        env = os.environ.copy()
        env["AEGIS_NO_FORENSICS"] = "1"
        env["AEGIS_NO_CLIP"] = "1"
        res = subprocess.run(
            [VENV_PYTHON, CLI_PATH] + args,
            env=env,
            capture_output=True,
            text=True,
            timeout=10 # prevent hangs
        )
        return {
            "status": "completed",
            "returncode": res.returncode,
            "stdout_snippet": res.stdout[-200:],
            "stderr_snippet": res.stderr[-200:],
            "crashed": res.returncode < 0 or "traceback" in res.stderr.lower() or "segmentation fault" in res.stderr.lower()
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "crashed": True,
            "reason": "Process hung / execution timed out after 10 seconds"
        }
    except Exception as e:
        return {
            "status": "error",
            "crashed": True,
            "reason": str(e)
        }

def fuzz_cli():
    print("[INFO] Starting CLI Fuzz Testing...")
    
    test_cases = []
    
    # Fuzz Case 1: Corrupted/invalid image inputs
    corrupted_images = ["empty.png", "truncated_header.png", "random_bytes.png", "text_disguised.png"]
    for ci in corrupted_images:
        path = os.path.join(BASE_TEMP, "corrupted_files", ci)
        if os.path.exists(path):
            test_cases.append({
                "name": f"corrupted_input_{ci}",
                "args": ["protect", "-i", path, "-o", os.path.join(BASE_TEMP, "transformed_images", "fuzz_out.png"), "--accept-ethics"]
            })
            
    # Fuzz Case 2: Out of bounds arguments for protect parameters
    test_cases.append({
        "name": "strength_negative",
        "args": ["protect", "-i", os.path.join(BASE_TEMP, "generated_images", "medium_256.png"), "-o", os.path.join(BASE_TEMP, "transformed_images", "fuzz_out.png"), "-s", "-100.0", "--accept-ethics"]
    })
    test_cases.append({
        "name": "strength_extremely_large",
        "args": ["protect", "-i", os.path.join(BASE_TEMP, "generated_images", "medium_256.png"), "-o", os.path.join(BASE_TEMP, "transformed_images", "fuzz_out.png"), "-s", "999999.9", "--accept-ethics"]
    })
    test_cases.append({
        "name": "eps_negative",
        "args": ["protect", "-i", os.path.join(BASE_TEMP, "generated_images", "medium_256.png"), "-o", os.path.join(BASE_TEMP, "transformed_images", "fuzz_out.png"), "--eps", "-5.0", "--accept-ethics"]
    })
    test_cases.append({
        "name": "steps_negative",
        "args": ["protect", "-i", os.path.join(BASE_TEMP, "generated_images", "medium_256.png"), "-o", os.path.join(BASE_TEMP, "transformed_images", "fuzz_out.png"), "--steps", "-10", "--accept-ethics"]
    })
    test_cases.append({
        "name": "steps_large",
        "args": ["protect", "-i", os.path.join(BASE_TEMP, "generated_images", "medium_256.png"), "-o", os.path.join(BASE_TEMP, "transformed_images", "fuzz_out.png"), "--steps", "5000", "--accept-ethics"]
    })
    
    # Fuzz Case 3: Malformed JSON metadata payload
    malformed_json_payloads = [
        "Not a JSON string at all",
        '{"unclosed_brace": 123',
        '{"invalid_quotes": \'single\'}',
        "{" + generate_random_string(1000),
        '{"author": "' + '\\' * 500 + '"}' # injection evasion / escape character fuzzing
    ]
    for idx, mj in enumerate(malformed_json_payloads):
        test_cases.append({
            "name": f"malformed_json_{idx}",
            "args": ["protect", "-i", os.path.join(BASE_TEMP, "generated_images", "medium_256.png"), "-o", os.path.join(BASE_TEMP, "transformed_images", "fuzz_out.png"), "-w", mj, "--accept-ethics"]
        })
        
    # Fuzz Case 4: Randomized CLI arguments
    for idx in range(10):
        random_args = [generate_random_string(random.randint(1, 10)) for _ in range(random.randint(2, 6))]
        test_cases.append({
            "name": f"random_cli_args_{idx}",
            "args": random_args
        })

    fuzz_results = []
    crashes_detected = 0
    
    for tc in test_cases:
        res = run_fuzz_case(tc["args"])
        res["name"] = tc["name"]
        res["args"] = tc["args"]
        fuzz_results.append(res)
        
        if res["crashed"]:
            crashes_detected += 1
            print(f"[CRASH] Fuzz case '{tc['name']}' triggered a crash/unhandled exception!")
            if "reason" in res:
                print(f"  Reason: {res['reason']}")
            else:
                print(f"  Stderr: {res['stderr_snippet']}")
        else:
            print(f"[PASS] Fuzz case '{tc['name']}' handled gracefully (exit code {res.get('returncode')}).")

    # Save fuzz report
    log_path = os.path.join(BASE_TEMP, "logs", "fuzzing_report.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(fuzz_results, f, indent=2)
        
    print(f"\n--- Fuzzing Summary ---")
    print(f"Total fuzz cases run: {len(test_cases)}")
    print(f"Crashes/Hangs detected: {crashes_detected}")
    print(f"Fuzz report saved to {log_path}")
    
    return crashes_detected == 0

if __name__ == "__main__":
    fuzz_cli()
