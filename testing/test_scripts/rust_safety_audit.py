import os
import re
import subprocess
import sys

RUST_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "aegis_kernel", "src", "lib.rs"))

def run_cargo_check():
    print("[INFO] Running 'cargo check' on aegis_kernel...")
    try:
        res = subprocess.run(
            ["cargo", "check"],
            cwd=os.path.dirname(os.path.dirname(RUST_SRC_PATH)),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if res.returncode == 0:
            print("[SUCCESS] 'cargo check' completed with no compile errors.")
            return True, res.stderr
        else:
            print(f"[ERROR] 'cargo check' failed with exit code {res.returncode}")
            print(res.stderr)
            return False, res.stderr
    except Exception as e:
        print(f"[ERROR] Failed to run cargo check: {e}")
        return False, str(e)

def scan_rust_source():
    print(f"[INFO] Auditing Rust source file: {RUST_SRC_PATH}")
    if not os.path.exists(RUST_SRC_PATH):
        print(f"[ERROR] Rust source file not found at {RUST_SRC_PATH}")
        return []

    with open(RUST_SRC_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    findings = []
    
    # Regex patterns
    unsafe_pattern = re.compile(r"\bunsafe\b")
    unwrap_pattern = re.compile(r"\.unwrap\s*\(")
    expect_pattern = re.compile(r"\.expect\s*\(")
    panic_pattern = re.compile(r"\b(panic!|unreachable!|todo!)\b")
    index_pattern = re.compile(r"\b(y_channel|decoded_bytes|extracted_bits|bits)\[[^\]]+\]") # Look specifically for variable indexing

    for i, line in enumerate(lines):
        line_num = i + 1
        clean_line = line.strip()
        
        # Skip comments
        if clean_line.startswith("//") or clean_line.startswith("/*") or clean_line.startswith("*"):
            continue

        # Check unsafe
        if unsafe_pattern.search(clean_line):
            findings.append({
                "type": "Unsafe Block",
                "line": line_num,
                "content": clean_line,
                "severity": "High",
                "desc": "Unsafe code bypasses Rust memory safety guarantees. Check for memory leaks or buffer overflows."
            })
            
        # Check unwrap
        if unwrap_pattern.search(clean_line):
            findings.append({
                "type": "Unwrap Call",
                "line": line_num,
                "content": clean_line,
                "severity": "Medium",
                "desc": "Calling unwrap() can trigger a runtime panic if the option/result is None/Err."
            })
            
        # Check expect
        if expect_pattern.search(clean_line):
            findings.append({
                "type": "Expect Call",
                "line": line_num,
                "content": clean_line,
                "severity": "Low",
                "desc": "Calling expect() can trigger a runtime panic. Ensure error message is meaningful."
            })

        # Check panic
        if panic_pattern.search(clean_line):
            findings.append({
                "type": "Panic Macro",
                "line": line_num,
                "content": clean_line,
                "severity": "High",
                "desc": "Explicit panics immediately crash the calling thread/process. Use proper error propagation (Result)."
            })

        # Check indexing which can cause panic if out of bounds
        if index_pattern.search(clean_line):
            findings.append({
                "type": "Unchecked Indexing",
                "line": line_num,
                "content": clean_line,
                "severity": "Medium",
                "desc": f"Unchecked array/slice indexing can cause runtime panic if index is out of bounds. Use .get() or check bounds first."
            })

    return findings

def main():
    success, cargo_output = run_cargo_check()
    findings = scan_rust_source()
    
    print("\n--- Rust Safety Audit Findings ---")
    if not findings:
        print("No critical Rust safety concerns detected in static analysis.")
    else:
        for f in findings:
            print(f"[{f['severity']}] Line {f['line']}: {f['type']}")
            print(f"  Code: {f['content']}")
            print(f"  Description: {f['desc']}\n")

    # Save report to logs/rust_safety_audit_report.json
    report = {
        "cargo_check_ok": success,
        "cargo_warnings": cargo_output,
        "findings": findings
    }
    log_path = os.path.join("testing", "logs", "rust_safety_audit_report.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        import json
        json.dump(report, f, indent=2)
    print(f"[INFO] Safety audit report saved to {log_path}")
    
    if any(f["severity"] == "High" for f in findings):
        print("[WARN] High severity issues found in Rust safety audit.")
        
    return findings

if __name__ == "__main__":
    main()
